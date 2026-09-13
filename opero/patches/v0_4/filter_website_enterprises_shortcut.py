"""Use the native website filter on the Enterprises shortcut only."""

import frappe


def execute():
	if not frappe.db.exists("Workspace", "Opero Website"):
		return
	workspace = frappe.get_doc("Workspace", "Opero Website")
	for row in workspace.shortcuts:
		if row.label == "Enterprises":
			row.type = "DocType"
			row.link_to = "Enterprise"
			row.doc_view = "List"
			row.stats_filter = '{"show_on_website":1}'
	workspace.save(ignore_permissions=True)
