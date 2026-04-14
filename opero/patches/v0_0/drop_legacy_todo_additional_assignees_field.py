import frappe


def execute():
	custom_field_name = frappe.db.exists("Custom Field", {"dt": "ToDo", "fieldname": "custom_additional_assignees"})
	if custom_field_name:
		frappe.delete_doc("Custom Field", custom_field_name, ignore_permissions=True, force=True)

	for property_setter_name in frappe.get_all(
		"Property Setter",
		filters={"doc_type": "ToDo", "field_name": "custom_additional_assignees"},
		pluck="name",
	):
		frappe.delete_doc("Property Setter", property_setter_name, ignore_permissions=True, force=True)

	columns = set(frappe.db.get_table_columns("ToDo"))
	if "custom_additional_assignees" in columns:
		frappe.db.sql_ddl("alter table `tabToDo` drop column `custom_additional_assignees`")

	frappe.clear_cache(doctype="ToDo")
