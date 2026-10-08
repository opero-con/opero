"""Require the main Project on every Timesheet, including API and import saves."""

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
	if not frappe.db.exists("DocType", "Timesheet"):
		return
	make_property_setter("Timesheet", "parent_project", "reqd", 1, "Check", validate_fields_for_doctype=False)
	frappe.clear_cache(doctype="Timesheet")
