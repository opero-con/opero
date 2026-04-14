import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"ToDo": [
				{
					"fieldname": "custom_section_break_ibyjh",
					"label": "",
					"fieldtype": "Section Break",
					"insert_after": "custom_is_group_child",
				},
				{
					"fieldname": "custom_column_break_th1rd",
					"label": "",
					"fieldtype": "Column Break",
					"insert_after": "status",
				},
				{
					"fieldname": "custom_column_break_mskkr",
					"label": "",
					"fieldtype": "Column Break",
					"insert_after": "priority",
				},
			]
		},
		ignore_validate=True,
		update=True,
	)

	# Keep the row explicitly split in 3 columns.
	_set_field_property("status", "insert_after", "custom_section_break_ibyjh", "Data")
	_set_field_property("priority", "insert_after", "custom_column_break_th1rd", "Data")
	_set_field_property("date", "insert_after", "custom_column_break_mskkr", "Data")


def _set_field_property(fieldname: str, property_name: str, value, property_type: str):
	filters = {
		"doctype_or_field": "DocField",
		"doc_type": "ToDo",
		"field_name": fieldname,
		"property": property_name,
	}
	property_setter = frappe.db.exists("Property Setter", filters)

	if property_setter:
		frappe.db.set_value(
			"Property Setter",
			property_setter,
			{
				"value": str(value),
				"property_type": property_type,
			},
			update_modified=False,
		)
		return

	frappe.make_property_setter(
		{
			"doctype_or_field": "DocField",
			"doctype": "ToDo",
			"fieldname": fieldname,
			"property": property_name,
			"value": value,
			"property_type": property_type,
		},
		validate_fields_for_doctype=False,
	)
