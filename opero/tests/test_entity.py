"""Entity scoping invariants.

Only the rules that would fail *silently*. A broken registry or a lock that
stops firing produces no error and no wrong-looking screen — the damage shows up
later as a document in the wrong entity's books. Everything here is therefore a
rule whose absence is invisible.

Deliberately not covered: naming prefixes, the display name, the access page and
the reports. Those announce themselves the moment they break.

	bench --site <site> run-tests --app opero
"""

from __future__ import annotations

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from opero import entity

# ERPNext ships these as test records, so the runner has them wherever it runs.
# Reused rather than created: standing up a Company drags in a chart of
# accounts, warehouses and modes of payment, which is slow and breaks on any
# site whose existing setup data is imperfect. These tests need two distinct
# entities, nothing more.
ENTITY_A = "_Test Company"
ENTITY_B = "_Test Company 1"


def _require_two_entities() -> tuple[str, str]:
	missing = [name for name in (ENTITY_A, ENTITY_B) if not frappe.db.exists("Company", name)]
	if missing:
		raise unittest.SkipTest(f"needs ERPNext test companies, missing: {', '.join(missing)}")
	return ENTITY_A, ENTITY_B


def _ensure_employee(company: str) -> str:
	existing = frappe.db.get_value("Employee", {"employee_name": "_Test Entity Manager"}, "name")
	if existing:
		return existing

	return (
		frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": "_Test Entity Manager",
				"gender": frappe.db.get_value("Gender", {}, "name"),
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2020-01-01",
				"status": "Active",
				"company": company,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


class TestEntityScoping(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.entity_a, cls.entity_b = _require_two_entities()
		# Left uncommitted on purpose: FrappeTestCase registers a rollback as
		# class cleanup, so this fixture disappears with the rest of the run.
		cls.manager = _ensure_employee(cls.entity_a)

	def _project(self, company: str) -> str:
		return (
			frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": frappe.generate_hash(length=10),
					"company": company,
					"custom_project_manager": self.manager,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	# -- the entity reaches the documents beneath the project ----------------

	def test_company_comes_from_the_project_not_the_caller(self):
		project = self._project(self.entity_a)

		task = frappe.get_doc(
			{
				"doctype": "Task",
				"subject": "entity scope",
				"project": project,
				"company": self.entity_b,  # deliberately wrong
			}
		).insert(ignore_permissions=True)

		self.assertEqual(task.company, self.entity_a)

	def test_company_follows_a_change_of_project(self):
		task = frappe.get_doc(
			{"doctype": "Task", "subject": "entity move", "project": self._project(self.entity_a)}
		).insert(ignore_permissions=True)
		self.assertEqual(task.company, self.entity_a)

		task.project = self._project(self.entity_b)
		task.save(ignore_permissions=True)

		self.assertEqual(task.company, self.entity_b)

	def test_entity_resolves_through_a_parent_document(self):
		"""Actual Spend has no project of its own; it reads its Cash Advance."""
		advance = frappe.get_doc(
			{
				"doctype": "Cash Advance-Reimbursable Form",
				"project": self._project(self.entity_b),
				"personnel": self.manager,
				"request_date": frappe.utils.nowdate(),
			}
		).insert(ignore_permissions=True)
		self.assertEqual(advance.company, self.entity_b)

		spend = frappe.get_doc(
			{
				"doctype": "Actual Spend",
				"cash_advance": advance.name,
				"claim_date": frappe.utils.nowdate(),
			}
		).insert(ignore_permissions=True)

		self.assertEqual(spend.company, self.entity_b)

	def test_every_registered_doctype_is_reachable(self):
		"""A registry entry naming a field that does not exist enforces nothing."""
		for doctype, scope in entity.active_project_scopes().items():
			meta = frappe.get_meta(scope.via[1] if scope.via else doctype)
			self.assertTrue(
				meta.has_field(scope.project_field),
				f"{doctype}: project field {scope.project_field!r} missing from {meta.name}",
			)
			self.assertTrue(
				frappe.get_meta(doctype).has_field(scope.company_field),
				f"{doctype}: company field {scope.company_field!r} missing",
			)

	# -- a document may not straddle two entities ----------------------------

	def test_child_row_in_another_entity_is_rejected(self):
		project_a = self._project(self.entity_a)
		project_b = self._project(self.entity_b)

		claim = frappe.get_doc(
			{
				"doctype": "Expense Claim",
				"employee": self.manager,
				"project": project_a,
				"expenses": [
					{
						"expense_date": frappe.utils.nowdate(),
						"project": project_b,
						"amount": 10,
						"sanctioned_amount": 10,
					}
				],
			}
		)

		with self.assertRaises(frappe.ValidationError):
			entity._reject_foreign_rows(claim, entity.PROJECT_SCOPED_DOCTYPES["Expense Claim"], self.entity_a)

	def test_submitted_document_refuses_to_change_entity(self):
		doc = frappe.get_doc({"doctype": "Task", "subject": "submitted"})
		doc.company = self.entity_a
		doc.docstatus = 1

		with self.assertRaises(frappe.ValidationError):
			entity._stamp_company(doc, "company", self.entity_b)

		self.assertEqual(doc.company, self.entity_a, "entity must not be rewritten in place")

	def test_draft_document_is_restamped_rather_than_refused(self):
		doc = frappe.get_doc({"doctype": "Task", "subject": "draft"})
		doc.company = self.entity_a
		doc.docstatus = 0

		entity._stamp_company(doc, "company", self.entity_b)

		self.assertEqual(doc.company, self.entity_b)

	# -- a project's entity is fixed once documents depend on it -------------

	def test_project_entity_changes_while_nothing_depends_on_it(self):
		project = self._project(self.entity_a)

		doc = frappe.get_doc("Project", project)
		doc.company = self.entity_b
		doc.save(ignore_permissions=True)

		self.assertEqual(frappe.db.get_value("Project", project, "company"), self.entity_b)

	def test_project_entity_locks_once_a_document_depends_on_it(self):
		project = self._project(self.entity_a)
		frappe.get_doc(
			{
				"doctype": "Budget Line",
				"project": project,
				"code": frappe.generate_hash(length=4),
				"description": "locks the project",
			}
		).insert(ignore_permissions=True)

		doc = frappe.get_doc("Project", project)
		doc.company = self.entity_b

		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

		self.assertEqual(frappe.db.get_value("Project", project, "company"), self.entity_a)

	def test_reports_hide_entities_the_user_may_not_see(self):
		"""Report SQL is raw, so it has to narrow rows itself."""
		from opero.opero.report.dynamic_timesheet.dynamic_timesheet import execute

		project = self._project(self.entity_b)
		task = frappe.get_doc(
			{"doctype": "Task", "subject": "hidden by permission", "project": project}
		).insert(ignore_permissions=True)

		# A dedicated user: an existing one may already carry Company permissions,
		# which would decide the outcome before the test does.
		user = "_test_entity_reader@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": "_Test Entity Reader",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": "Company",
				"for_value": self.entity_a,
				"apply_to_all_doctypes": 1,
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache(user=user)

		frappe.set_user(user)
		try:
			self.assertEqual(entity.get_permitted_companies(), [self.entity_a])
			subjects = {row.get("task_subject") for row in execute({})[1]}
			self.assertNotIn(task.subject, subjects)
		finally:
			frappe.set_user("Administrator")

	def test_lock_lookup_agrees_with_the_guard(self):
		"""The form reads one total; the guard counts per DocType. They must agree."""
		project = self._project(self.entity_a)
		self.assertFalse(entity.get_project_lock(project)["locked"])

		frappe.get_doc(
			{
				"doctype": "Budget Line",
				"project": project,
				"code": frappe.generate_hash(length=4),
				"description": "counted",
			}
		).insert(ignore_permissions=True)

		lock = entity.get_project_lock(project)
		self.assertTrue(lock["locked"])
		self.assertEqual(lock["count"], sum(entity.count_project_documents(project).values()))
