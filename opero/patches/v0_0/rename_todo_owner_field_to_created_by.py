import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	old_custom_field_name = frappe.db.exists("Custom Field", {"dt": "ToDo", "fieldname": "custom_owner"})

	create_custom_fields(
		{
			"ToDo": [
				{
					"fieldname": "custom_created_by",
					"label": "Created By",
					"fieldtype": "Link",
					"options": "User",
					"insert_after": "assigned_by",
					"read_only": 1,
					"no_copy": 1,
				}
			]
		},
		update=True,
	)

	columns = set(frappe.db.get_table_columns("ToDo"))
	if "custom_created_by" in columns and "custom_owner" in columns:
		frappe.db.sql(
			"""
			update `tabToDo`
			set custom_created_by = ifnull(nullif(custom_created_by, ''), ifnull(nullif(custom_owner, ''), owner))
			"""
		)
	elif "custom_created_by" in columns:
		frappe.db.sql(
			"""
			update `tabToDo`
			set custom_created_by = owner
			where ifnull(custom_created_by, '') = ''
			"""
		)

	if old_custom_field_name:
		frappe.db.set_value(
			"Custom Field",
			old_custom_field_name,
			{
				"hidden": 1,
				"read_only": 1,
			},
			update_modified=False,
		)
