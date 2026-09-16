from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from opero import todo_dashboard
from opero import todo_enhancements
from opero.opero.report.todo_assignee_load_and_risk import todo_assignee_load_and_risk
from opero.opero.report.todo_created_vs_closed import todo_created_vs_closed
from opero.opero.report.todo_explorer import todo_explorer
from opero.opero.report.todo_in_progress_aging import todo_in_progress_aging


class TestTodoPermissions(FrappeTestCase):
	def test_owner_has_document_permission(self):
		doc = SimpleNamespace(
			owner="owner@example.test",
			allocated_to=None,
			assigned_by=None,
			custom_assignees=[],
		)
		with patch.object(todo_enhancements, "_has_unrestricted_todo_access", return_value=False):
			self.assertTrue(todo_enhancements.has_permission(doc, user="owner@example.test"))

	def test_permission_query_includes_every_supported_relationship(self):
		with (
			patch.object(todo_enhancements, "_has_unrestricted_todo_access", return_value=False),
			patch.object(frappe.db, "escape", return_value="'user@example.test'"),
		):
			condition = todo_enhancements.get_permission_query_conditions("user@example.test")

		self.assertIn("`tabToDo`.owner", condition)
		self.assertIn("`tabToDo`.allocated_to", condition)
		self.assertIn("`tabToDo`.assigned_by", condition)
		self.assertIn("`tabToDo Assignee`.user", condition)

	def test_dashboard_scope_is_unrestricted_only_for_privileged_role(self):
		with (
			patch.object(frappe, "session", SimpleNamespace(user="manager@example.test")),
			patch.object(todo_enhancements, "_has_unrestricted_todo_access", return_value=True),
		):
			self.assertEqual(todo_dashboard.get_user_scope_condition(), ("1 = 1", []))

	def test_dashboard_scope_includes_owner_and_assigned_by(self):
		with (
			patch.object(frappe, "session", SimpleNamespace(user="user@example.test")),
			patch.object(todo_enhancements, "_has_unrestricted_todo_access", return_value=False),
		):
			condition, params = todo_dashboard.get_user_scope_condition()

		self.assertIn("todo.owner", condition)
		self.assertIn("todo.assigned_by", condition)
		self.assertEqual(params, ["user@example.test"] * 4)


class TestTodoAssignmentNotifications(FrappeTestCase):
	def test_only_new_assignees_are_notified(self):
		previous = SimpleNamespace(custom_assignees=[SimpleNamespace(user="existing@example.test")])
		doc = SimpleNamespace(
			name="TODO-1",
			status="Open",
			custom_title="A task",
			custom_assignees=[
				SimpleNamespace(user="existing@example.test"),
				SimpleNamespace(user="new@example.test"),
			],
			get_doc_before_save=lambda: previous,
		)

		with (
			patch.object(frappe, "get_all", return_value=["new@example.test"]) as get_all,
			patch.object(frappe, "sendmail") as sendmail,
			patch.object(frappe.utils, "get_url_to_form", return_value="https://example.test/todo/TODO-1"),
		):
			todo_enhancements._send_assignment_email(doc)

		get_all.assert_called_once()
		self.assertEqual(get_all.call_args.kwargs["filters"]["name"], ("in", ["new@example.test"]))
		sendmail.assert_called_once()
		self.assertEqual(sendmail.call_args.kwargs["recipients"], ["new@example.test"])

	def test_unchanged_assignees_are_not_notified(self):
		assignees = [SimpleNamespace(user="existing@example.test")]
		doc = SimpleNamespace(
			name="TODO-1",
			status="Open",
			custom_title="A task",
			custom_assignees=assignees,
			get_doc_before_save=lambda: SimpleNamespace(custom_assignees=assignees),
		)

		with patch.object(frappe, "sendmail") as sendmail:
			todo_enhancements._send_assignment_email(doc)

		sendmail.assert_not_called()


class TestTodoReportScoping(FrappeTestCase):
	def assert_report_applies_scope(self, get_data, filters=None):
		with (
			patch.object(todo_dashboard, "get_user_scope_condition", return_value=("todo.owner = %s", ["me"])),
			patch.object(frappe.db, "sql", return_value=[]) as sql,
		):
			get_data(frappe._dict(filters or {}))

		query, params = sql.call_args.args[:2]
		self.assertIn("todo.owner = %s", query)
		self.assertIn("me", params)

	def test_explorer_filters_cannot_bypass_scope(self):
		self.assert_report_applies_scope(todo_explorer.get_data, {"assignee": "other@example.test"})
		self.assert_report_applies_scope(todo_explorer.get_data, {"unassigned_only": 1})

	def test_aging_show_all_cannot_bypass_scope(self):
		self.assert_report_applies_scope(todo_in_progress_aging.get_data, {"show_all": 1})

	def test_assignee_load_applies_scope(self):
		self.assert_report_applies_scope(todo_assignee_load_and_risk.get_data)

	def test_created_vs_closed_applies_scope(self):
		with (
			patch.object(todo_dashboard, "get_entity_condition", return_value=("", [])),
			patch.object(todo_dashboard, "get_user_scope_condition", return_value=("todo.owner = %s", ["me"])),
			patch.object(frappe.db, "sql", return_value=[]) as sql,
		):
			todo_created_vs_closed.execute({"time_window": "Last 30 Days"})

		todo_queries = [call for call in sql.call_args_list if "FROM `tabToDo` todo" in call.args[0]]
		self.assertEqual(len(todo_queries), 3)
		for call in todo_queries:
			query, params = call.args[:2]
			self.assertIn("todo.owner = %s", query)
			self.assertIn("me", params)
