"""Reload Opero Website so Desk shows the public-site shortcuts.

After the DocType rename, a site can keep a Workspace row whose shortcuts
still point at Opero Site * names that no longer exist. Desk then filters
every tile out and the page looks empty.
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
