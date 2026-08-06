"""Let each entity carry a short display name separate from its legal name.

A Company record is named after its registered legal name, which is what belongs
on invoices and in the ledger but is long and near-identical between entities in
every link field, filter and report column.

Frappe can show a title in place of the stored name wherever a link is
rendered — form fields, link dropdowns, list views and report columns all run
through the same formatter, which falls back to the stored name when the title
is empty. So filling in Display Name changes what people read without touching
what documents record.

The names themselves are data: they are typed into each Company record, not
carried in this repository.
"""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

DISPLAY_FIELD = "custom_display_name"


def execute():
	create_custom_fields(
		{
			"Company": [
				{
					"fieldname": DISPLAY_FIELD,
					"label": "Display Name",
					"fieldtype": "Data",
					"insert_after": "abbr",
					"description": (
						"Short name shown wherever this company appears in the interface. "
						"Documents and reports keep the registered name."
					),
				}
			]
		},
		update=True,
	)

	_set_doctype_property("title_field", DISPLAY_FIELD, "Data")
	_set_doctype_property("show_title_field_in_link", "1", "Check")
	# Makes the entity findable by its short name in link dropdowns and search,
	# without discarding search fields the site already configured.
	_set_doctype_property("search_fields", _merged_search_fields(), "Data")

	frappe.clear_cache(doctype="Company")


def _merged_search_fields() -> str:
	"""Add the display name and abbreviation to whatever is already searched."""
	current = frappe.get_meta("Company").search_fields or ""
	fields = [field.strip() for field in current.split(",") if field.strip()]
	for field in (DISPLAY_FIELD, "abbr"):
		if field not in fields:
			fields.append(field)
	return ",".join(fields)


def _set_doctype_property(property_name: str, value: str, property_type: str) -> None:
	name = f"Company-main-{property_name}"
	if frappe.db.exists("Property Setter", name):
		frappe.db.set_value("Property Setter", name, "value", value)
		return

	make_property_setter(
		"Company",
		"",
		property_name,
		value,
		property_type,
		for_doctype=True,
		validate_fields_for_doctype=False,
	)
