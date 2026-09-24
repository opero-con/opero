"""Use compact, separator-free IDs for new Timesheets."""

from __future__ import annotations

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

NAMING_SERIES = "TS.YY.WW.##"


def execute():
	if not frappe.db.exists("DocType", "Timesheet"):
		return

	_set_property("default", NAMING_SERIES)
	_set_property("options", NAMING_SERIES)
	frappe.clear_cache(doctype="Timesheet")


def _set_property(property_name: str, value: str) -> None:
	name = f"Timesheet-naming_series-{property_name}"
	if frappe.db.exists("Property Setter", name):
		frappe.db.set_value("Property Setter", name, "value", value)
		return

	make_property_setter(
		"Timesheet",
		"naming_series",
		property_name,
		value,
		"Text",
		validate_fields_for_doctype=False,
	)
