import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"ToDo": [
				{
					"fieldname": "custom_cancelled_on",
					"label": "Cancelled On",
					"fieldtype": "Datetime",
					"insert_after": "custom_closed_on",
					"read_only": 1,
					"hidden": 1,
					"no_copy": 1,
				}
			]
		},
		update=True,
	)

	columns = set(frappe.db.get_table_columns("ToDo"))
	if "custom_cancelled_on" not in columns:
		return

	# Backfill historical cancelled tasks so helper text can reference cancellation date.
	frappe.db.sql(
		"""
		update `tabToDo`
		set custom_cancelled_on = modified
		where status = 'Cancelled'
		and ifnull(custom_cancelled_on, '') = ''
		"""
	)
