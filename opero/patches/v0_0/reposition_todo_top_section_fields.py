import frappe
import json


def execute():
	_normalize_field_order_property()

	_set_custom_field_insert_after("custom_assignees", "column_break_2")
	_set_custom_field_insert_after("custom_parent_todo", "color")
	_set_custom_field_insert_after("custom_assignment_group", "custom_parent_todo")
	_set_custom_field_insert_after("custom_is_group_child", "custom_assignment_group")

	# Place Assignees at the top of column 2.
	_set_field_property("custom_assignees", "insert_after", "column_break_2", "Data")

	# Keep Color and Parent ToDo in column 1 of the same section.
	_set_field_property("color", "insert_after", "custom_title", "Data")
	_set_field_property("custom_parent_todo", "insert_after", "color", "Data")

	frappe.clear_cache(doctype="ToDo")


def _normalize_field_order_property():
	property_setter_name = frappe.db.exists(
		"Property Setter",
		{"doctype_or_field": "DocType", "doc_type": "ToDo", "property": "field_order"},
	)
	if not property_setter_name:
		return

	raw_order = frappe.db.get_value("Property Setter", property_setter_name, "value")
	if not raw_order:
		return

	try:
		field_order = json.loads(raw_order)
	except Exception:
		return

	if not isinstance(field_order, list):
		return

	field_order = [field for field in field_order if field != "custom_additional_assignees"]

	target_chain = [
		"custom_title",
		"color",
		"custom_parent_todo",
		"custom_assignment_group",
		"custom_is_group_child",
		"column_break_2",
		"custom_assignees",
		"allocated_to",
	]

	for field in target_chain:
		while field in field_order:
			field_order.remove(field)

	if "description_and_status" in field_order:
		insert_at = field_order.index("description_and_status") + 1
	else:
		insert_at = 0

	for offset, field in enumerate(target_chain):
		field_order.insert(insert_at + offset, field)

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


def _set_custom_field_insert_after(fieldname: str, insert_after: str):
	custom_field_name = frappe.db.exists("Custom Field", {"dt": "ToDo", "fieldname": fieldname})
	if not custom_field_name:
		return

	frappe.db.set_value(
		"Custom Field",
		custom_field_name,
		{"insert_after": insert_after},
		update_modified=False,
	)
