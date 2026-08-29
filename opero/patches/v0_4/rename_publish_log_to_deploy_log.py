"""Publisher deploys the site; the batches it records are Deploy Log, not Publish Log."""

from __future__ import annotations

import frappe


def execute():
	if frappe.db.exists("DocType", "Publish Log") and not frappe.db.exists("DocType", "Deploy Log"):
		frappe.rename_doc("DocType", "Publish Log", "Deploy Log", force=True)
	elif frappe.db.exists("DocType", "Publish Log") and frappe.db.exists("DocType", "Deploy Log"):
		frappe.delete_doc("DocType", "Publish Log", force=True, ignore_permissions=True)
