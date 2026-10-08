"""Required Projects and permission-aware personnel allocation choices."""

from inspect import unwrap
from unittest import TestCase
from unittest.mock import patch

import frappe

from opero.api import timesheet as api
from opero.events import timesheet


class TestTimesheetProjects(TestCase):
	def test_missing_project_is_rejected(self):
		with patch.object(timesheet.frappe, "throw", side_effect=ValueError) as throw:
			with self.assertRaises(ValueError):
				timesheet._validate_budgeted_project(frappe._dict(parent_project=None, employee="EMP-1"))
			self.assertEqual(throw.call_args.kwargs["title"], "Project required")

	def test_project_needs_personnel_allocation(self):
		with (
			patch.object(timesheet, "get_budgeted_projects", return_value=["PROJ-1"]),
			patch.object(timesheet.frappe, "throw", side_effect=ValueError),
		):
			timesheet._validate_budgeted_project(frappe._dict(parent_project="PROJ-1", employee="EMP-1"))
			with self.assertRaises(ValueError):
				timesheet._validate_budgeted_project(frappe._dict(parent_project="PROJ-2", employee="EMP-1"))

	def test_no_personnel_returns_no_projects(self):
		with patch.object(api, "frappe") as mocked:
			mocked.parse_json.return_value = {}
			self.assertEqual(unwrap(api.get_personnel_projects)("Project", "", "name", 0, 20, {}), [])
			mocked.get_list.assert_not_called()

	def test_project_search_preserves_permissions_and_customer(self):
		with (
			patch.object(api, "frappe") as mocked,
			patch.object(timesheet, "get_budgeted_projects", return_value=["PROJ-1"]),
		):
			mocked.parse_json.return_value = {"employee": "EMP-1", "customer": "CUSTOMER-1"}
			mocked.get_list.return_value = [frappe._dict(name="PROJ-1", project_name="Survey")]
			self.assertEqual(
				unwrap(api.get_personnel_projects)("Project", "Sur", "name", 2, 10, {}),
				[["PROJ-1", "Survey"]],
			)
			mocked.get_doc.return_value.check_permission.assert_called_once_with("read")
			args, kwargs = mocked.get_list.call_args
			self.assertEqual(args, ("Project",))
			self.assertEqual(
				kwargs["filters"], {"name": ["in", ["PROJ-1"]], "status": "Open", "customer": "CUSTOMER-1"}
			)
			self.assertEqual(kwargs["limit_start"], 2)
			self.assertEqual(kwargs["limit_page_length"], 10)

	def test_unreadable_employee_cannot_be_searched(self):
		with (
			patch.object(api, "frappe") as mocked,
			patch.object(timesheet, "get_budgeted_projects") as projects,
		):
			mocked.parse_json.return_value = {"employee": "EMP-1"}
			mocked.get_doc.return_value.check_permission.side_effect = frappe.PermissionError
			with self.assertRaises(frappe.PermissionError):
				unwrap(api.get_personnel_projects)("Project", "", "name", 0, 20, {})
			projects.assert_not_called()
