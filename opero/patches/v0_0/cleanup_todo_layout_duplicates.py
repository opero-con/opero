import frappe

from opero.patches.v0_0.apply_todo_three_column_meta_layout import execute as apply_todo_three_column_meta_layout


KEEP_COLUMN_BREAKS = {"custom_column_break_th1rd", "custom_column_break_mskkr"}
ROW_COLUMN_BREAK_ANCHORS = {"status", "priority", "custom_column_break_th1rd", "custom_column_break_mskkr"}


def execute():
	apply_todo_three_column_meta_layout()
	_remove_conflicting_column_breaks()

	# Re-assert desired 3-column row order.
	_set_field_property("status", "insert_after", "custom_section_break_ibyjh", "Data")
	_set_field_property("priority", "insert_after", "custom_column_break_th1rd", "Data")
	_set_field_property("date", "insert_after", "custom_column_break_mskkr", "Data")
	_set_field_property("email_sent", "hidden", "0", "Check")

	frappe.clear_cache(doctype="ToDo")


def _remove_conflicting_column_breaks():
	rows = frappe.get_all(
		"Custom Field",
		filters={"dt": "ToDo", "fieldtype": "Column Break"},
		fields=["name", "fieldname", "insert_after"],
	)

	fields_to_delete: set[str] = set()
	for row in rows:
		fieldname = (row.fieldname or "").strip()
		insert_after = (row.insert_after or "").strip()
		if not fieldname or fieldname in KEEP_COLUMN_BREAKS:
			continue
		if insert_after in ROW_COLUMN_BREAK_ANCHORS:
			fields_to_delete.add(row.name)

	for custom_field_name in fields_to_delete:
		if frappe.db.exists("Custom Field", custom_field_name):
			fieldname = frappe.db.get_value("Custom Field", custom_field_name, "fieldname")
			_delete_property_setters_for_field(fieldname)
			frappe.delete_doc("Custom Field", custom_field_name, ignore_permissions=True, force=True)


def _delete_property_setters_for_field(fieldname: str | None):
	if not fieldname:
		return

	for property_setter_name in frappe.get_all(
		"Property Setter",
		filters={"doc_type": "ToDo", "field_name": fieldname},
		pluck="name",
	):
		frappe.delete_doc("Property Setter", property_setter_name, ignore_permissions=True, force=True)


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
