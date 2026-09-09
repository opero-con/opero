"""Open the Enterprises workspace link with Show on website enabled."""

from __future__ import annotations

import frappe


def execute():
	frappe.reload_doc("opero_site", "page", "website_enterprises", force=True)
	if not frappe.db.exists("Workspace", "Opero Website"):
		return

	workspace = frappe.get_doc("Workspace", "Opero Website")
	for link in workspace.links:
		if link.label == "Enterprises":
			link.link_type = "Page"
			link.link_to = "website-enterprises"
			workspace.save(ignore_permissions=True)
			return

	frappe.throw("Enterprises link not found in Opero Website workspace.")
