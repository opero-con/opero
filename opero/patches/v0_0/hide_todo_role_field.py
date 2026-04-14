import frappe


def execute():
	_set_field_property("role", "hidden", "1", "Check")


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
