"""Add Publication Types to the Opero Website Setup card on existing sites."""

from __future__ import annotations

import frappe


def execute():
	frappe.reload_doc("opero_site", "workspace", "opero_website", force=True)
	if not frappe.db.exists("Workspace", "Opero Website"):
		return

	doc = frappe.get_doc("Workspace", "Opero Website")
	links = {row.label: row.link_to for row in doc.links if row.type == "Link"}
	if links.get("Publication Types") != "Publication Type":
		frappe.throw("Opero Website workspace reloaded without Publication Types.")
