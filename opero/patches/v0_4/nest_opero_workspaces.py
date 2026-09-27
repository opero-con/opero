"""Replace Opero Website and ToDo Hub with their nested Opero workspaces."""

from __future__ import annotations

import frappe

REPLACEMENTS = {"Opero Website": "Site Content", "ToDo Hub": "Approvals"}


def execute():
	for old, new in REPLACEMENTS.items():
		if not frappe.db.exists("Workspace", new):
			frappe.throw(f"Workspace {new} was not synced; keeping {old}.")
		if frappe.db.exists("Workspace", old):
			frappe.delete_doc("Workspace", old, ignore_permissions=True, force=True)
	frappe.clear_cache(doctype="Workspace")
