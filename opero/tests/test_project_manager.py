"""Project owns its manager; open documents follow it."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.events import project as project_events


class TestProjectManager(FrappeTestCase):
	def setUp(self):
		self.old_pm = self._manager("Old PM")
		self.new_pm = self._manager("New PM")
		self.project = self._record(
			"Project",
			project_name="PM source " + frappe.generate_hash(length=12),
			**self._project_values(self.old_pm),
		)

	def _record(self, doctype, **values):
		doc = frappe.get_doc(
			dict(doctype=doctype, name="pm-test-" + frappe.generate_hash(length=12), **values)
		)
		doc.db_insert()
		return doc.name

	def _manager(self, name):
		email = frappe.scrub(name) + "-" + frappe.generate_hash(length=6) + "@example.com"
		employee = self._record("Employee", first_name=name, employee_name=name, user_id=email)
		return frappe._dict(employee=employee, name=name, email=email)

	def _project_values(self, manager):
		return {
			"custom_project_manager": manager.employee,
			"custom_pm_name": manager.name,
			"custom_pm_email": manager.email,
		}

	def _timesheet(self, docstatus, **values):
		return self._record(
			"Timesheet", parent_project=self.project, docstatus=docstatus, start_date="2026-01-01", **values
		)

	def test_save_copies_manager_from_project(self):
		timesheet = frappe.get_doc(
			doctype="Timesheet", parent_project=self.project, custom_pm_email="stale@example.com"
		)
		project_events.copy_project_manager(timesheet)
		self.assertEqual(timesheet.custom_pm_email, self.old_pm.email)
		self.assertEqual(timesheet.custom_project_manager, self.old_pm.employee)
		self.assertEqual(timesheet.custom_pm_name, "Old PM")

		advance = frappe.get_doc(doctype="Cash Advance-Reimbursable Form", project=self.project)
		project_events.copy_project_manager(advance)
		self.assertEqual((advance.project_manager, advance.pm_email), ("Old PM", self.old_pm.email))

		task = frappe.get_doc(doctype="Consultant Task", project=self.project)
		project_events.copy_project_manager(task)
		self.assertEqual(
			(task.project_manager, task.pm_name, task.pm_email),
			(self.old_pm.employee, "Old PM", self.old_pm.email),
		)

	def test_manager_name_and_email_come_from_the_employee(self):
		frappe.db.set_value("Project", self.project, {"custom_pm_name": "", "custom_pm_email": ""})
		manager = project_events.get_project_manager(self.project)
		self.assertEqual((manager.custom_pm_name, manager.custom_pm_email), ("Old PM", self.old_pm.email))

	def test_save_without_project_clears_manager(self):
		timesheet = frappe.get_doc(doctype="Timesheet", custom_pm_email="stale@example.com")
		project_events.copy_project_manager(timesheet)
		self.assertIsNone(timesheet.custom_pm_email)

	def test_sync_moves_open_documents_and_keeps_finished_ones(self):
		pending = self._timesheet(0, custom_pm_email=self.old_pm.email)
		approved = self._timesheet(1, custom_pm_email=self.old_pm.email)
		advance = self._record(
			"Cash Advance-Reimbursable Form", project=self.project, docstatus=0, pm_email=self.old_pm.email
		)
		frappe.db.set_value("Project", self.project, self._project_values(self.new_pm))

		project_events.sync_project_manager(self.project)

		self.assertEqual(
			frappe.db.get_value(
				"Timesheet", pending, ["custom_pm_email", "custom_project_manager", "custom_pm_name"]
			),
			(self.new_pm.email, self.new_pm.employee, "New PM"),
		)
		self.assertEqual(frappe.db.get_value("Timesheet", approved, "custom_pm_email"), self.old_pm.email)
		self.assertEqual(
			frappe.db.get_value("Cash Advance-Reimbursable Form", advance, "pm_email"), self.new_pm.email
		)

	def test_project_update_syncs_only_when_manager_changes(self):
		doc = frappe.get_doc("Project", self.project)
		doc._doc_before_save = frappe.copy_doc(doc)
		with patch.object(project_events, "sync_project_manager") as sync:
			project_events.on_update_project(doc)
			sync.assert_not_called()
			doc.custom_pm_email = self.new_pm.email
			project_events.on_update_project(doc)
			sync.assert_not_called()
			doc.custom_project_manager = self.new_pm.employee
			project_events.on_update_project(doc)
			sync.assert_called_once_with(self.project)
