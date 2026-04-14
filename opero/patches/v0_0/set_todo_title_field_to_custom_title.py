import frappe


def execute():
	_set_doctype_property("title_field", "custom_title", "Data")
	_set_doctype_property("search_fields", "custom_title, description, reference_type, reference_name", "Data")


def _set_doctype_property(property_name: str, value, property_type: str):
	filters = {
		"doctype_or_field": "DocType",
		"doc_type": "ToDo",
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
			"doctype_or_field": "DocType",
			"doctype": "ToDo",
			"property": property_name,
			"value": value,
			"property_type": property_type,
		},
		validate_fields_for_doctype=False,
	)
