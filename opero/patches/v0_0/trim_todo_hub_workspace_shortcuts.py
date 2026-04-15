from __future__ import annotations

"""Remove the Team Load & Risk and In Progress Aging shortcuts from the
ToDo Hub workspace.  Both reports are already accessible via the card link
section, so the shortcuts are redundant.
"""

import json

import frappe

WORKSPACE_NAME = "ToDo Hub"


def execute():
	if not frappe.db.exists("Workspace", WORKSPACE_NAME):
		return

	doc = frappe.get_doc("Workspace", WORKSPACE_NAME)

	KEEP = {"Flow Hub", "New ToDo", "My ToDos"}
	doc.set(
		"shortcuts",
		[s for s in doc.shortcuts if (s.label or s.link_to) in KEEP],
	)

	# Rebuild content to drop the removed shortcut blocks
	try:
		content = json.loads(doc.content or "[]")
	except (ValueError, TypeError):
		content = []

	shortcut_labels = {s.label for s in doc.shortcuts}
	content = [
		block for block in content
		if not (
			block.get("type") == "shortcut"
			and block.get("data", {}).get("shortcut_name") not in shortcut_labels
		)
	]
	doc.content = json.dumps(content, separators=(",", ":"))

	doc.save(ignore_permissions=True)
	frappe.clear_cache(doctype="Workspace")
