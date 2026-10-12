"""Sync the leave approval shortcut even when workspace timestamps match."""

import frappe


def execute():
	frappe.reload_doc("opero", "workspace", "approvals", force=True)
	frappe.clear_cache(doctype="Workspace")
