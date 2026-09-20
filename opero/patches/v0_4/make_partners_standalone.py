"""Promote homepage Partner child rows to standalone website content records."""

import frappe


def execute():
	if not frappe.db.table_exists("Partner"):
		return

	frappe.reload_doc("opero_site", "doctype", "partner")
	columns = set(frappe.db.get_table_columns("Partner"))
	if {"parent", "parenttype", "parentfield"}.issubset(columns):
		frappe.db.sql(
			"""
			UPDATE `tabPartner`
			SET website_status = CASE WHEN show_on_website = 1 THEN 'Published' ELSE 'Unpublished' END,
				parent = NULL, parenttype = NULL, parentfield = NULL
			WHERE parenttype = 'Partners'
			"""
		)

	if frappe.db.exists("DocType", "Partners"):
		frappe.delete_doc("DocType", "Partners", force=True, ignore_permissions=True)

	frappe.reload_doc("opero_site", "workspace", "opero_website", force=True)
	frappe.clear_cache(doctype="Partner")
