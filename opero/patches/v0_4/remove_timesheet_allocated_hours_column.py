"""Remove allocated hours from the grid now that the form shows allocation balances."""

import frappe


def execute():
	name = "Timesheet Detail-custom_a_hrs"
	if not frappe.db.exists("Custom Field", name):
		return
	field = frappe.get_doc("Custom Field", name)
	field.in_list_view = 0
	field.save()
	frappe.clear_cache(doctype="Timesheet Detail")
