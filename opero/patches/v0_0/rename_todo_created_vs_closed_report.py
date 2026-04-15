from __future__ import annotations

import frappe


def execute():
	if frappe.db.exists("Report", "ToDo Created vs Closed 30d") and not frappe.db.exists(
		"Report", "ToDo Created vs Closed"
	):
		frappe.rename_doc("Report", "ToDo Created vs Closed 30d", "ToDo Created vs Closed", force=True)
