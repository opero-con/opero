import json

import frappe


ANCHOR_FIELD = "description_and_status"
OBSOLETE_FIELDS = {"custom_additional_assignees"}
MANAGED_FIELD_ORDER_SEGMENT = [
	"custom_title",
	"color",
	"custom_parent_todo",
	"column_break_2",
	"custom_assignees",
	"allocated_to",
	"custom_assignment_group",
	"custom_is_group_child",
	"custom_section_break_ibyjh",
	"status",
	"custom_column_break_th1rd",
	"priority",
	"custom_column_break_mskkr",
	"date",
]

CUSTOM_FIELD_INSERT_AFTER = {
	"custom_title": "description_and_status",
	"custom_parent_todo": "color",
	"custom_assignment_group": "allocated_to",
	"custom_is_group_child": "custom_assignment_group",
	"custom_assignees": "column_break_2",
	"custom_section_break_ibyjh": "custom_is_group_child",
	"custom_column_break_th1rd": "status",
	"custom_column_break_mskkr": "priority",
}

DOCFIELD_INSERT_AFTER = {
	"custom_title": "description_and_status",
	"custom_parent_todo": "color",
	"custom_assignees": "column_break_2",
	"custom_assignment_group": "allocated_to",
	"custom_is_group_child": "custom_assignment_group",
	"color": "custom_title",
	"allocated_to": "custom_assignees",
	"status": "custom_section_break_ibyjh",
	"priority": "custom_column_break_th1rd",
	"date": "custom_column_break_mskkr",
}


def execute():
	_pin_field_order()
	_pin_custom_field_anchors()
	_pin_docfield_anchors()
	frappe.clear_cache(doctype="ToDo")


def _pin_field_order():
	field_order = _get_current_field_order()
	if not field_order:
		return

	existing_fields = _get_existing_fieldnames()
	managed_fields = [field for field in MANAGED_FIELD_ORDER_SEGMENT if field in existing_fields]

	normalized = [field for field in field_order if field not in OBSOLETE_FIELDS and field not in managed_fields]
	insert_index = normalized.index(ANCHOR_FIELD) + 1 if ANCHOR_FIELD in normalized else 0

	for offset, field in enumerate(managed_fields):
		normalized.insert(insert_index + offset, field)

	_set_doctype_field_order_property(normalized)


def _get_current_field_order() -> list[str]:
	property_setter_name = frappe.db.exists(
		"Property Setter",
		{"doctype_or_field": "DocType", "doc_type": "ToDo", "property": "field_order"},
	)
	if property_setter_name:
		raw_order = frappe.db.get_value("Property Setter", property_setter_name, "value")
		try:
			parsed = json.loads(raw_order or "[]")
			if isinstance(parsed, list):
				return parsed
		except Exception:
			pass

	meta = frappe.get_meta("ToDo")
	return [d.fieldname for d in (meta.fields or []) if d.fieldname]


def _get_existing_fieldnames() -> set[str]:
	meta = frappe.get_meta("ToDo")
	return {d.fieldname for d in (meta.fields or []) if d.fieldname}


def _pin_custom_field_anchors():
	for fieldname, insert_after in CUSTOM_FIELD_INSERT_AFTER.items():
		custom_field_name = frappe.db.exists("Custom Field", {"dt": "ToDo", "fieldname": fieldname})
		if not custom_field_name:
			continue

		frappe.db.set_value(
			"Custom Field",
			custom_field_name,
			{"insert_after": insert_after},
			update_modified=False,
		)


def _pin_docfield_anchors():
	for fieldname, insert_after in DOCFIELD_INSERT_AFTER.items():
		_set_field_property(fieldname, "insert_after", insert_after, "Data")


def _set_doctype_field_order_property(field_order: list[str]):
	value = json.dumps(field_order)
	filters = {"doctype_or_field": "DocType", "doc_type": "ToDo", "property": "field_order"}
	property_setter = frappe.db.exists("Property Setter", filters)

	if property_setter:
		frappe.db.set_value(
			"Property Setter",
			property_setter,
			{"value": value, "property_type": "Data"},
			update_modified=False,
		)
		return

	frappe.make_property_setter(
		{
			"doctype_or_field": "DocType",
			"doctype": "ToDo",
			"property": "field_order",
			"value": value,
			"property_type": "Data",
		},
		validate_fields_for_doctype=False,
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
