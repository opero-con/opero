"""Narrow hidden workspaces to Workspace Managers who are also System Managers.

Frappe shows hidden workspaces to every Workspace Manager, and most Opero staff
hold that role, so hiding Frappe's Website workspace alone would not reach them.
"""

from __future__ import annotations

import frappe
from frappe.desk import desktop


@frappe.whitelist()
def get_workspace_sidebar_items():
	sidebar = desktop.get_workspace_sidebar_items()
	sidebar["pages"] = filter_hidden_workspaces(sidebar["pages"])
	return sidebar


def filter_hidden_workspaces(pages):
	if "System Manager" in frappe.get_roles():
		return pages
	return [page for page in pages if not (page.get("public") and page.get("is_hidden"))]
