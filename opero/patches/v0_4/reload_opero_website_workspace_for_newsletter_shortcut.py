"""Add the filtered Newsletter List shortcut to existing sites."""

from __future__ import annotations

import frappe


def execute():
	frappe.reload_doc("opero_site", "workspace", "opero_website", force=True)
	if not frappe.db.exists("Workspace", "Opero Website"):
		return

	doc = frappe.get_doc("Workspace", "Opero Website")
	shortcut = next((row for row in doc.shortcuts if row.label == "Newsletter List"), None)
	expected_filter = '[["Contact Mailing List","mailing_list","like","%Newsletter%"]]'
	if not shortcut or shortcut.link_to != "Contact" or shortcut.stats_filter != expected_filter:
		frappe.throw("Opero Website workspace reloaded without the Newsletter List shortcut.")
