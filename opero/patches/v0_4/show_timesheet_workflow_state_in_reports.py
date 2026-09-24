"""Expose Timesheet workflow state to Report/List column pickers."""

from __future__ import annotations

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
	if not frappe.db.exists("Custom Field", "Timesheet-workflow_state"):
		return

	_set_property("hidden", "0")
	_set_property("in_list_view", "1")
	_set_property("in_standard_filter", "1")
	frappe.clear_cache(doctype="Timesheet")


def _set_property(property_name: str, value: str) -> None:
	name = f"Timesheet-workflow_state-{property_name}"
	if frappe.db.exists("Property Setter", name):
		frappe.db.set_value("Property Setter", name, "value", value)
		return

	make_property_setter(
		"Timesheet",
		"workflow_state",
		property_name,
		value,
		"Check",
		validate_fields_for_doctype=False,
	)
