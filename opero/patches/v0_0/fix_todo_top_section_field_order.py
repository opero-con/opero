import json

import frappe


REMOVED_FIELDS = {"custom_additional_assignees"}
TOP_SECTION_CHAIN = [
	"custom_title",
	"custom_assignees",
	"column_break_2",
	"color",
	"allocated_to",
	"custom_parent_todo",
	"custom_assignment_group",
	"custom_is_group_child",
]


def execute():
	_set_insert_after_defaults()
	_update_field_order_property_setter()
	frappe.clear_cache(doctype="ToDo")


def _set_insert_after_defaults():
	_set_field_property("custom_assignees", "insert_after", "custom_title", "Data")
	_set_field_property("color", "insert_after", "column_break_2", "Data")
	_set_field_property("allocated_to", "insert_after", "color", "Data")
	_set_field_property("custom_parent_todo", "insert_after", "allocated_to", "Data")
	_set_field_property("custom_assignment_group", "insert_after", "custom_parent_todo", "Data")
	_set_field_property("custom_is_group_child", "insert_after", "custom_assignment_group", "Data")


def _update_field_order_property_setter():
	property_setter_name = frappe.db.exists(
		"Property Setter",
		{"doctype_or_field": "DocType", "doc_type": "ToDo", "property": "field_order"},
	)
	if not property_setter_name:
		return

	raw_field_order = frappe.db.get_value("Property Setter", property_setter_name, "value")
	if not raw_field_order:
		return

	try:
		field_order = json.loads(raw_field_order)
	except Exception:
		return

	if not isinstance(field_order, list):
		return

	field_order = [field for field in field_order if field not in REMOVED_FIELDS]

	for field in TOP_SECTION_CHAIN:
		while field in field_order:
			field_order.remove(field)

	insert_after = "description_and_status"
	if insert_after in field_order:
		insert_index = field_order.index(insert_after) + 1
	else:
		insert_index = 0

	for offset, field in enumerate(TOP_SECTION_CHAIN):
		field_order.insert(insert_index + offset, field)

	frappe.db.set_value(
		"Property Setter",
		property_setter_name,
		{"value": json.dumps(field_order)},
		update_modified=False,
	)


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
