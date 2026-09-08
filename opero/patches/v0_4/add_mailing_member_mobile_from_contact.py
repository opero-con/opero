"""Fetch Contact mobile onto Email Group Member for list/export."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Email Group Member": [
				{
					"fieldname": "custom_mobile_no",
					"label": "Mobile No",
					"fieldtype": "Data",
					"options": "Phone",
					"insert_after": "custom_contact",
					"fetch_from": "custom_contact.mobile_no",
					"read_only": 1,
					"depends_on": "eval:doc.custom_contact",
					"in_list_view": 1,
					"module": "Opero",
				},
			]
		},
		update=True,
	)
	# Backfill members that already have a Contact link.
	frappe.db.sql(
		"""
		update `tabEmail Group Member` member
		inner join `tabContact` contact on contact.name = member.custom_contact
		set member.custom_mobile_no = contact.mobile_no
		where ifnull(member.custom_contact, '') != ''
		"""
	)
	frappe.db.sql(
		"""
		update `tabEmail Group Member`
		set custom_mobile_no = null
		where ifnull(custom_contact, '') = ''
		"""
	)
	frappe.clear_cache(doctype="Email Group Member")
