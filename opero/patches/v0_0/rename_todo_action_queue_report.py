from __future__ import annotations

"""Rename the 'ToDo Action Queue' report to 'ToDo Explorer'."""

import frappe

OLD_NAME = "ToDo Action Queue"
NEW_NAME = "ToDo Explorer"


def execute():
	if not frappe.db.exists("Report", OLD_NAME):
		return
	if frappe.db.exists("Report", NEW_NAME):
		return

	frappe.rename_doc("Report", OLD_NAME, NEW_NAME, force=True)

	for table in ("tabWorkspace Link", "tabWorkspace Shortcut"):
		frappe.db.sql(
			f"UPDATE `{table}` SET link_to = %s WHERE link_to = %s",
			(NEW_NAME, OLD_NAME),
		)

	frappe.clear_cache(doctype="Workspace")
