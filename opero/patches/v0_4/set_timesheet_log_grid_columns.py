"""Show only Task, From Time and Hrs in the Timesheet time-log grid."""

from __future__ import annotations

import json

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

GRID_COLUMNS = {"task": 5, "from_time": 4, "hours": 1}


def execute():
	if not frappe.db.exists("DocType", "Timesheet Detail"):
		return

	meta = frappe.get_meta("Timesheet Detail")
	for field in meta.fields:
		in_grid = field.fieldname in GRID_COLUMNS
		if bool(field.in_list_view) != in_grid:
			_set_property(field.fieldname, "in_list_view", "1" if in_grid else "0", "Check")
		if in_grid:
			_set_property(field.fieldname, "columns", str(GRID_COLUMNS[field.fieldname]), "Int")

	order = list(GRID_COLUMNS) + [
		field.fieldname for field in meta.fields if field.fieldname not in GRID_COLUMNS
	]
	_set_field_order(order)
	frappe.clear_cache(doctype="Timesheet Detail")


def _set_property(fieldname: str, property_name: str, value: str, property_type: str) -> None:
	name = f"Timesheet Detail-{fieldname}-{property_name}"
	if frappe.db.exists("Property Setter", name):
		frappe.db.set_value("Property Setter", name, "value", value)
		return

	make_property_setter(
		"Timesheet Detail",
		fieldname,
		property_name,
		value,
		property_type,
		validate_fields_for_doctype=False,
	)


def _set_field_order(order: list[str]) -> None:
	name = "Timesheet Detail-main-field_order"
	value = json.dumps(order)
	if frappe.db.exists("Property Setter", name):
		frappe.db.set_value("Property Setter", name, "value", value)
		return

	make_property_setter(
		"Timesheet Detail",
		None,
		"field_order",
		value,
		"Data",
		for_doctype=True,
		validate_fields_for_doctype=False,
	)
