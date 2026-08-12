"""Replace Project hours metric fields with a single HTML summary.

Allocated hours, used hours and % progress were three separate read-only
controls. The values stay on the document for reports; the form shows one
summary instead.
"""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

HIDDEN_FIELDS = (
	"custom_column_break_eszdr",
	"custom_allocated_hours",
	"custom_column_break_h6iui",
	"actual_time",
	"custom_column_break_y80wz",
	"custom_percent_progress",
)


def execute():
	create_custom_fields(
		{
			"Project": [
				{
					"fieldname": "custom_hours_summary",
					"label": "Hours",
					"fieldtype": "HTML",
					"insert_after": "custom_section_break_fdfzy",
				}
			]
		},
		update=True,
	)

	_set_field_property("custom_section_break_fdfzy", "label", "Hours", "Data")
	for fieldname in HIDDEN_FIELDS:
		_set_field_property(fieldname, "hidden", "1", "Check")

	frappe.clear_cache(doctype="Project")


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
