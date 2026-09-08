"""Reuse Email Groups; preserve existing subscriptions and expose Contact memberships."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	for name in ("contact_mailing_list", "mailing_membership_event"):
		frappe.reload_doc("opero", "doctype", name)
	create_custom_fields(
		{
			"Contact": [
				{
					"fieldname": "custom_mailing_section",
					"label": "Mailing Lists",
					"fieldtype": "Section Break",
					"insert_after": "email_ids",
					"module": "Opero",
				},
				{
					"fieldname": "custom_mailing_lists",
					"label": "Mailing Lists",
					"fieldtype": "Table MultiSelect",
					"options": "Contact Mailing List",
					"insert_after": "custom_mailing_section",
					"module": "Opero",
					"description": "Memberships use the primary email. Contacts sharing that address share memberships. Saving does not send email.",
				},
				{
					"fieldname": "custom_mailing_status",
					"label": "Subscription Status",
					"fieldtype": "HTML",
					"insert_after": "custom_mailing_lists",
					"module": "Opero",
				},
				{
					"fieldname": "custom_after_mailing_section",
					"fieldtype": "Section Break",
					"insert_after": "custom_mailing_status",
					"module": "Opero",
				},
			],
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
	frappe.db.sql(
		"update `tabEmail Group Member` set custom_confirmation_status='Confirmed' where coalesce(custom_confirmation_status, '')=''"
	)
	from opero.mailing.membership import sync_email

	for email in set(frappe.get_all("Email Group Member", pluck="email")):
		sync_email(email)
	# Select-only access lets Contact editors validate links without exposing subscriber records.
	from frappe.permissions import add_permission

	if not frappe.db.exists(
		"Custom DocPerm", {"parent": "Email Group", "role": "All", "permlevel": 0, "if_owner": 0}
	):
		add_permission("Email Group", "All", ptype="select")
	frappe.clear_cache()
