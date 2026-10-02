"""Offer Timesheet Detail's Task Name to Report view so exports carry the task's name, not its ID."""

from __future__ import annotations

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
	if not frappe.db.exists("Custom Field", "Timesheet Detail-custom_project_task"):
		return

	_set_property("hidden", "0")
	_set_property("read_only", "1")
	frappe.clear_cache(doctype="Timesheet Detail")


def _set_property(property_name: str, value: str) -> None:
	name = f"Timesheet Detail-custom_project_task-{property_name}"
	if frappe.db.exists("Property Setter", name):
		frappe.db.set_value("Property Setter", name, "value", value)
		return

	make_property_setter(
		"Timesheet Detail",
		"custom_project_task",
		property_name,
		value,
		"Check",
		validate_fields_for_doctype=False,
	)
