"""Reload Opero Website so the split Home sections replace the Home Page card link."""

from __future__ import annotations

import frappe


def execute():
	frappe.reload_doc("opero_site", "workspace", "opero_website", force=True)
	if not frappe.db.exists("Workspace", "Opero Website"):
		return
	doc = frappe.get_doc("Workspace", "Opero Website")
	if not doc.shortcuts:
		frappe.throw("Opero Website workspace reloaded without shortcuts.")
