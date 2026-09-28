"""Hide Frappe's Website workspace; Opero's Site Content replaces it.

`opero.workspace_sidebar` keeps hidden workspaces for System Managers who are
also Workspace Managers.
"""

import frappe


def execute():
	if not frappe.db.exists("Workspace", "Website"):
		return
	frappe.db.set_value("Workspace", "Website", "is_hidden", 1)
	frappe.clear_cache(doctype="Workspace")
