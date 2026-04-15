from __future__ import annotations

"""Restore the Flow Hub shortcut in the ToDo Hub workspace to 'flow-hub'.

The create_flow_hub_workspace_v2 patch changed the link_to from 'flow-hub'
to 'opero-flow-hub'. After reverting that experiment the page is back at
'flow-hub', so the shortcut needs to match.
"""

import frappe

WORKSPACE_NAME = "ToDo Hub"


def execute():
	if not frappe.db.exists("Workspace", WORKSPACE_NAME):
		return

	doc = frappe.get_doc("Workspace", WORKSPACE_NAME)
	updated = False

	for shortcut in doc.shortcuts:
		if shortcut.type == "Page" and shortcut.link_to == "opero-flow-hub":
			shortcut.link_to = "flow-hub"
			updated = True

	if updated:
		doc.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Workspace")
