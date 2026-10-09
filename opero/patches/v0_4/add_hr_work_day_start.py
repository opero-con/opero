"""Keep the generated task-log start beside Standard Working Hours in HR Settings."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"HR Settings": [
				{
					"fieldname": "custom_work_day_starts_at",
					"label": "Timesheet starts at",
					"fieldtype": "Time",
					"insert_after": "standard_working_hours",
					"default": "08:30:00",
					"reqd": 1,
					"description": "",
				}
			]
		}
	)
	current_start = frappe.db.get_single_value("HR Settings", "custom_work_day_starts_at")
	if current_start is None or current_start == "":
		frappe.db.set_single_value("HR Settings", "custom_work_day_starts_at", "08:30:00")
	frappe.clear_cache(doctype="HR Settings")
