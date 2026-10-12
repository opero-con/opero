"""Give new ToDos a readable identifier with a counter for each year."""

import frappe

SERIES = "TDO-.YY.###"


def execute():
	frappe.make_property_setter(
		{
			"doctype_or_field": "DocType",
			"doctype": "ToDo",
			"property": "autoname",
			"value": SERIES,
			"property_type": "Data",
		},
		validate_fields_for_doctype=False,
	)
	frappe.clear_cache(doctype="ToDo")
