import frappe
from frappe.tests.utils import FrappeTestCase


class TestTimesheetWorkflow(FrappeTestCase):
	def test_list_columns_preserve_workflow_report_visibility(self):
		meta = frappe.get_meta("Timesheet")
		workflow_state = meta.get_field("workflow_state")
		self.assertFalse(workflow_state.in_list_view)
		self.assertFalse(workflow_state.hidden)
		self.assertTrue(workflow_state.in_standard_filter)
		for fieldname in ("custom_project_manager", "per_billed"):
			self.assertFalse(meta.get_field(fieldname).in_list_view)
		for fieldname in ("start_date", "end_date", "total_hours"):
			with self.subTest(fieldname=fieldname):
				field = meta.get_field(fieldname)
				self.assertTrue(field.in_list_view)
				self.assertFalse(field.hidden)

	def test_system_managers_can_cancel_approved_timesheets(self):
		roles = frappe.get_all(
			"Workflow Transition",
			filters={
				"parent": "Timesheet Approval",
				"state": "Approved",
				"action": "Cancel",
				"next_state": "Cancelled",
			},
			pluck="allowed",
		)

		self.assertIn("Projects Manager", roles)
		self.assertIn("System Manager", roles)
