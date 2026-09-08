"""Drop confirmation requests; members are active until they unsubscribe."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	frappe.db.sql(
		"update `tabEmail Group Member` set custom_confirmation_status='Confirmed' where custom_confirmation_status != 'Confirmed'"
	)
	create_custom_fields(
		{
			"Email Group Member": [
				{
					"fieldname": "custom_confirmation_status",
					"label": "Subscription Status",
					"fieldtype": "Select",
					"options": "Confirmed",
					"default": "Confirmed",
					"read_only": 1,
					"in_list_view": 1,
					"in_standard_filter": 1,
					"insert_after": "email",
					"module": "Opero",
					"description": "Members are eligible until they unsubscribe from a newsletter footer link. Newsletter Managers can reactivate by clearing Unsubscribed.",
				},
			],
		},
		update=True,
	)
	for doctype in ("Mailing Confirmation Request", "Mailing Confirmation Item"):
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)
	from opero.mailing.membership import sync_email

	for email in set(frappe.get_all("Email Group Member", pluck="email")):
		sync_email(email)
	frappe.clear_cache()
