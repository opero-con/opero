"""Add Communication Source and reload the Website Enquiries shortcut."""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Communication": [
				{
					"fieldname": "custom_source",
					"label": "Source",
					"fieldtype": "Select",
					"options": "\nWebsite",
					"insert_after": "sent_or_received",
					"in_standard_filter": 1,
					"in_list_view": 1,
					"module": "Opero Site",
				}
			]
		},
		update=True,
	)
	frappe.reload_doc("opero_site", "workspace", "opero_website", force=True)
	if not frappe.db.exists("Workspace", "Opero Website"):
		return
	doc = frappe.get_doc("Workspace", "Opero Website")
	if not any(row.label == "Website Enquiries" for row in doc.shortcuts):
		frappe.throw("Opero Website workspace reloaded without Website Enquiries.")
