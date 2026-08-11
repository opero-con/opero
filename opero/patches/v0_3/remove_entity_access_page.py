"""Remove the Entity Access desk page (Company User Permission manager)."""

from __future__ import annotations

import frappe


def execute():
	if frappe.db.exists("Page", "entity-access"):
		frappe.delete_doc("Page", "entity-access", force=1, ignore_permissions=True)
