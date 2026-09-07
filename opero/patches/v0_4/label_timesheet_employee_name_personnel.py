"""Label Timesheet employee_name as Personnel for export pickers.

Keeps the field unhidden in meta (form hide stays in timesheet.js).
"""

from __future__ import annotations

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
	if not frappe.db.exists("DocType", "Timesheet"):
		return

	_set_property("employee_name", "label", "Personnel", "Data")
	_set_property("employee_name", "hidden", "0", "Check")
	frappe.clear_cache(doctype="Timesheet")


def _set_property(fieldname: str, property_name: str, value: str, property_type: str) -> None:
	name = f"Timesheet-{fieldname}-{property_name}"
	if frappe.db.exists("Property Setter", name):
		frappe.db.set_value("Property Setter", name, "value", value)
		return

	make_property_setter(
		"Timesheet",
		fieldname,
		property_name,
		value,
		property_type,
		validate_fields_for_doctype=False,
	)
