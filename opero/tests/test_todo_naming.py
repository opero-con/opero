from datetime import datetime
from unittest.mock import patch

import frappe
from frappe.desk.form import assign_to
from frappe.model.naming import set_new_name
from frappe.tests.utils import FrappeTestCase

from opero.patches.v0_4.set_todo_naming_series import SERIES, execute


class TestTodoNaming(FrappeTestCase):
	def test_sequence_resets_with_the_year_and_migration_does_not_reset_it(self):
		frappe.db.savepoint("todo_naming_sequence")
		try:
			frappe.db.sql("delete from `tabSeries` where name in (%s, %s)", ("TDO-26", "TDO-27"))
			execute()
			self.assertEqual(frappe.get_meta("ToDo").autoname, SERIES)
			with patch("frappe.model.naming.now_datetime", return_value=datetime(2026, 10, 12)):
				self.assertEqual(self._name(), "TDO-26001")
				execute()
				self.assertEqual(self._name(), "TDO-26002")
			with patch("frappe.model.naming.now_datetime", return_value=datetime(2027, 1, 1)):
				self.assertEqual(self._name(), "TDO-27001")
			with patch("frappe.model.naming.now_datetime", return_value=datetime(2026, 12, 31)):
				self.assertEqual(self._name(), "TDO-26003")
		finally:
			frappe.db.rollback(save_point="todo_naming_sequence")
			frappe.clear_cache(doctype="ToDo")

	def test_counter_grows_beyond_three_digits(self):
		frappe.db.savepoint("todo_naming_overflow")
		try:
			execute()
			with patch("frappe.model.naming.now_datetime", return_value=datetime(2026, 10, 12)):
				self._name()
				frappe.db.sql("update `tabSeries` set current=999 where name=%s", "TDO-26")
				self.assertEqual(self._name(), "TDO-261000")
		finally:
			frappe.db.rollback(save_point="todo_naming_overflow")
			frappe.clear_cache(doctype="ToDo")

	def test_assignment_todos_use_the_series_without_renaming_existing_records(self):
		with self.set_user("Administrator"):
			frappe.db.savepoint("todo_assignment_naming")
			try:
				existing = set(frappe.get_all("ToDo", pluck="name"))
				execute()
				note = frappe.get_doc({"doctype": "Note", "title": "ToDo naming test"}).insert()
				with patch("frappe.desk.form.assign_to.notify_assignment"):
					assign_to.add({"doctype": "Note", "name": note.name, "assign_to": ["Administrator"]})
				name = frappe.db.get_value(
					"ToDo", {"reference_type": "Note", "reference_name": note.name}, "name"
				)
				self.assertRegex(name, r"^TDO-\d{2}\d{3,}$")
				self.assertTrue(existing.issubset(set(frappe.get_all("ToDo", pluck="name"))))
			finally:
				frappe.db.rollback(save_point="todo_assignment_naming")
				frappe.clear_cache(doctype="ToDo")

	def _name(self):
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Naming test"})
		set_new_name(doc)
		return doc.name
