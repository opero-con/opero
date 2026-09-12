"""Use native Employee links with a website filter only on the Team shortcut."""

import frappe


def execute():
	if not frappe.db.exists("Workspace", "Opero Website"):
		return
	workspace = frappe.get_doc("Workspace", "Opero Website")
	for row in workspace.links:
		if row.label == "Team":
			row.link_type = "DocType"
			row.link_to = "Employee"
	for row in workspace.shortcuts:
		if row.label == "Team":
			row.type = "DocType"
			row.link_to = "Employee"
			row.doc_view = "List"
			row.stats_filter = '{"show_on_website":1}'
	workspace.save(ignore_permissions=True)
