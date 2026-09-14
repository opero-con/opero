"""Keep week metadata exportable without displaying it in the timesheet grid."""

import frappe


def execute():
	name = "Timesheet Detail-custom_week_of_month"
	if not frappe.db.exists("Custom Field", name):
		return
	field = frappe.get_doc("Custom Field", name)
	field.in_list_view = 0
	field.save()
	frappe.clear_cache(doctype="Timesheet Detail")
