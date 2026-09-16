import frappe


def execute():
	custom_field = frappe.db.exists(
		"Custom Field",
		{"dt": "ToDo", "fieldname": "custom_assignees"},
	)
	if not custom_field:
		return

	frappe.db.set_value(
		"Custom Field",
		custom_field,
		"description",
		None,
		update_modified=False,
	)
	frappe.clear_cache(doctype="ToDo")
