import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"ToDo": [
				{
					"fieldname": "custom_closed_on",
					"label": "Closed On",
					"fieldtype": "Datetime",
					"insert_after": "date",
					"read_only": 1,
					"hidden": 1,
					"no_copy": 1,
				}
			]
		},
		update=True,
	)

	columns = set(frappe.db.get_table_columns("ToDo"))
	if "custom_closed_on" not in columns:
		return

	# Backfill historical closed tasks so "Closed ..." helper text has a reference date.
	frappe.db.sql(
		"""
		update `tabToDo`
		set custom_closed_on = modified
		where status = 'Closed'
		and ifnull(custom_closed_on, '') = ''
		"""
	)
