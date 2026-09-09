"""Rename the split home section DocTypes without the Home prefix."""

from __future__ import annotations

import frappe


RENAMES = (
	("Home Hero", "Hero"),
	("Home About", "About"),
	("Home Pillars", "Pillars"),
	("Home Impacts", "Impacts"),
	("Home Projects", "Projects"),
	("Home Partners", "Partners"),
)


def execute():
	for old, new in RENAMES:
		if not frappe.db.exists("DocType", old):
			continue

		# Model sync creates the destination from its renamed JSON before patches run.
		# Remove that empty definition so Frappe's DocType rename can migrate Singles,
		# child parent types, links, attachments, and customizations normally.
		if frappe.db.exists("DocType", new):
			frappe.delete_doc("DocType", new, force=True, ignore_permissions=True)

		frappe.rename_doc("DocType", old, new, force=True)
		frappe.reload_doc("opero_site", "doctype", frappe.scrub(new), force=True)
	frappe.reload_doc("opero_site", "workspace", "opero_website", force=True)
