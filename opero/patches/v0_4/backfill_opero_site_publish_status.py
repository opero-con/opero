"""Existing public-site records are already live; mark them Published."""

from __future__ import annotations

import frappe

DOCTYPES = (
	("opero_site", "publication"),
	("opero_site", "team_member"),
	("opero_site", "home_page"),
	("opero_site", "privacy"),
	("opero_site", "site_settings"),
)


def execute():
	for module, doctype in DOCTYPES:
		frappe.reload_doc(module, "doctype", doctype)

	if frappe.db.has_column("Publication", "status"):
		frappe.db.sql(
			"""
			UPDATE `tabPublication`
			SET status = 'Published', unpublish = 0
			WHERE IFNULL(status, '') = ''
			"""
		)

	if frappe.db.has_column("Team Member", "status"):
		hidden = (
			"show_on_website = 0"
			if frappe.db.has_column("Team Member", "show_on_website")
			else "0 = 1"
		)
		frappe.db.sql(
			f"""
			UPDATE `tabTeam Member`
			SET
				status = CASE WHEN {hidden} THEN 'Unpublished' ELSE 'Published' END,
				unpublish = CASE WHEN {hidden} THEN 1 ELSE 0 END
			WHERE IFNULL(status, '') = ''
			"""
		)

	for name in ("Home Page", "Privacy", "Site Settings"):
		if not frappe.db.exists("DocType", name):
			continue
		if frappe.db.get_single_value(name, "status"):
			continue
		frappe.db.set_value(name, name, "status", "Published", update_modified=False)
		frappe.db.set_value(name, name, "unpublish", 0, update_modified=False)
