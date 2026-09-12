"""Expose filtered Team navigation without granting access to HR records."""

import frappe


def execute():
	frappe.reload_doc("opero_site", "page", "website_team", force=True)
	if not frappe.db.exists("Workspace", "Opero Website"):
		return
	workspace = frappe.get_doc("Workspace", "Opero Website")
	for row in workspace.links:
		if row.label == "Team":
			row.link_type = "Page"
			row.link_to = "website-team"
	for row in workspace.shortcuts:
		if row.label == "Team":
			row.type = "Page"
			row.link_to = "website-team"
			row.doc_view = ""
			row.stats_filter = ""
	workspace.save(ignore_permissions=True)
