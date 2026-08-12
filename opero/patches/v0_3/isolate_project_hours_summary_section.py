"""Keep the Hours summary alone in its section so it stays full width.

Frappe still builds Column Break columns even when those breaks are hidden, so
leaving the old metric column breaks in the Hours section squeezed the HTML
summary into a col-sm-3 and wrapped the label.
"""

from __future__ import annotations

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

RAW_HOURS_FIELDS = [
	"custom_column_break_eszdr",
	"custom_allocated_hours",
	"custom_column_break_h6iui",
	"actual_time",
	"custom_column_break_y80wz",
	"custom_percent_progress",
]

HOURS_SECTION = [
	"custom_section_break_fdfzy",
	"custom_hours_summary",
	"custom_section_break_hours_raw",
	*RAW_HOURS_FIELDS,
]


def execute():
	create_custom_fields(
		{
			"Project": [
				{
					"fieldname": "custom_section_break_hours_raw",
					"label": "Hours (raw)",
					"fieldtype": "Section Break",
					"insert_after": "custom_hours_summary",
					"hidden": 1,
				}
			]
		},
		update=True,
	)
	_set_field_property("custom_section_break_hours_raw", "hidden", "1", "Check")
	_reorder_field_order()
	frappe.clear_cache(doctype="Project")


def _reorder_field_order() -> None:
	name = "Project-main-field_order"
	current = frappe.db.get_value("Property Setter", name, "value")
	if not current:
		return

	order = json.loads(current)
	drop = set(HOURS_SECTION)
	without = [f for f in order if f not in drop]
	anchor = len(without)
	if "percent_complete" in without:
		anchor = without.index("percent_complete") + 1
	elif "custom_section_break_rttw7" in without:
		anchor = without.index("custom_section_break_rttw7")
	fixed = without[:anchor] + HOURS_SECTION + without[anchor:]
	frappe.db.set_value("Property Setter", name, "value", json.dumps(fixed))


def _set_field_property(fieldname: str, property_name: str, value: str, property_type: str) -> None:
	name = f"Project-{fieldname}-{property_name}"
	if frappe.db.exists("Property Setter", name):
		frappe.db.set_value("Property Setter", name, "value", value)
		return

	make_property_setter(
		"Project",
		fieldname,
		property_name,
		value,
		property_type,
		validate_fields_for_doctype=False,
	)
