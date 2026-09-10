"""Keep only the Opero Website Enterprises shortcut filtered for publishing."""

from __future__ import annotations

import frappe


def execute():
	frappe.reload_doc("opero_site", "workspace", "opero_website", force=True)
	if not frappe.db.exists("Workspace", "Opero Website"):
		return

	workspace = frappe.get_doc("Workspace", "Opero Website")
	for link in workspace.links:
		if link.label == "Enterprises":
			link.link_type = "DocType"
			link.link_to = "Enterprise"

	for shortcut in workspace.shortcuts:
		if shortcut.label == "Enterprises":
			shortcut.type = "Page"
			shortcut.link_to = "website-enterprises"

	workspace.save(ignore_permissions=True)
