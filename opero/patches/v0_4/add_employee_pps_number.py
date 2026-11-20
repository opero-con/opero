"""Add the Irish PPS Number to Employee for payslips and Revenue payroll submissions."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Employee": [
				{
					"fieldname": "pps_number",
					"label": "PPS Number",
					"fieldtype": "Data",
					"insert_after": "salary_mode",
					"description": "Irish Personal Public Service Number, for example 1234567FA.",
				}
			]
		},
		update=True,
	)
	frappe.clear_cache(doctype="Employee")
