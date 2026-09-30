"""Allow System Managers to cancel approved Timesheets through the workflow."""

import frappe


WORKFLOW = "Timesheet Approval"
TRANSITION = {
	"state": "Approved",
	"action": "Cancel",
	"next_state": "Cancelled",
	"allowed": "System Manager",
	"allow_self_approval": 1,
}


def execute():
	if not frappe.db.exists("Workflow", WORKFLOW):
		return

	workflow = frappe.get_doc("Workflow", WORKFLOW)
	if any(
		row.state == TRANSITION["state"]
		and row.action == TRANSITION["action"]
		and row.next_state == TRANSITION["next_state"]
		and row.allowed == TRANSITION["allowed"]
		for row in workflow.transitions
	):
		return

	workflow.append("transitions", TRANSITION)
	workflow.save(ignore_permissions=True)
	frappe.clear_cache(doctype="Timesheet")
