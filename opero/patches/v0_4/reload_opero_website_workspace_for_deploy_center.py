"""Reload Opero Website so its shortcut/link point at Deploy Center, not Publisher.

Workspace Link/Shortcut `link_to` is Data, so the DocType rename does not
update it. Mirrors reload_opero_website_workspace.py for the earlier rename.
"""

from __future__ import annotations

import frappe


def execute():
	frappe.reload_doc("opero_site", "workspace", "opero_website", force=True)
	if not frappe.db.exists("Workspace", "Opero Website"):
		return
	doc = frappe.get_doc("Workspace", "Opero Website")
	if not doc.shortcuts:
		frappe.throw("Opero Website workspace reloaded without shortcuts.")
