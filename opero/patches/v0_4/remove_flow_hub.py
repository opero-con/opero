"""Retire the custom ToDo page and use the standard ToDo views and reports."""

import json

import frappe


def execute():
	frappe.reload_doc("opero", "workspace", "approvals", force=True)
	for name in ("flow-hub", "opero-flow-hub"):
		# Remove links from custom workspaces before deleting the page they reference.
		for row in frappe.get_all(
			"Workspace Shortcut",
			filters={"type": "Page", "link_to": name},
			fields=["name", "parent", "label"],
		):
			workspace = frappe.get_doc("Workspace", row.parent)
			workspace.set(
				"shortcuts", [shortcut for shortcut in workspace.shortcuts if shortcut.name != row.name]
			)
			if workspace.content:
				blocks = json.loads(workspace.content)
				workspace.content = json.dumps(
					[
						block
						for block in blocks
						if not (
							block.get("type") == "shortcut"
							and block.get("data", {}).get("shortcut_name") == row.label
						)
					]
				)
			workspace.save(ignore_permissions=True)
		frappe.db.delete("Workspace Link", {"link_type": "Page", "link_to": name})
		if frappe.db.exists("Page", name):
			frappe.delete_doc("Page", name, ignore_permissions=True)
	frappe.clear_cache()
