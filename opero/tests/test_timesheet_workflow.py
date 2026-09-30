import frappe
from frappe.tests.utils import FrappeTestCase


class TestTimesheetWorkflow(FrappeTestCase):
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
