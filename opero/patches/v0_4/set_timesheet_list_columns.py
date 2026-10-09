"""Show timesheet dates and hours without duplicating the workflow indicator."""

import frappe

from opero.patches.v0_4.show_timesheet_employee_name import _set_property


def execute():
	for fieldname in ("workflow_state", "custom_project_manager", "per_billed"):
		_set_property(fieldname, "in_list_view", "0", "Check")
	for fieldname in ("start_date", "end_date", "total_hours"):
		_set_property(fieldname, "hidden", "0", "Check")
		_set_property(fieldname, "in_list_view", "1", "Check")
	frappe.clear_cache(doctype="Timesheet")
