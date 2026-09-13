"""Swap Personnel Type and Series without replacing the rest of Employee's layout."""

import json

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
	order = [field.fieldname for field in frappe.get_meta("Employee").fields]
	if "custom_personnel_type" not in order or "naming_series" not in order:
		return
	type_index = order.index("custom_personnel_type")
	series_index = order.index("naming_series")
	if type_index < series_index:
		return
	order[type_index], order[series_index] = order[series_index], order[type_index]
	make_property_setter(
		"Employee", None, "field_order", json.dumps(order), "Data",
		for_doctype=True, validate_fields_for_doctype=False,
	)
	frappe.db.set_value(
		"Custom Field", "Employee-custom_personnel_type", "insert_after",
		order[series_index - 1] if series_index else "",
	)
	frappe.clear_cache(doctype="Employee")
