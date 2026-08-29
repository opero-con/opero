"""The page deploys the site; it does not just publish, so Publisher becomes Deploy Center."""

from __future__ import annotations

import frappe


def execute():
	if frappe.db.exists("DocType", "Publisher") and not frappe.db.exists("DocType", "Deploy Center"):
		frappe.rename_doc("DocType", "Publisher", "Deploy Center", force=True)
	elif frappe.db.exists("DocType", "Publisher") and frappe.db.exists("DocType", "Deploy Center"):
		frappe.delete_doc("DocType", "Publisher", force=True, ignore_permissions=True)

	# Publisher/Deploy Center is a Single: its child rows' `parent` equals the
	# doctype's own name. rename_doc() fixes `parenttype` but leaves `parent`
	# stale, which orphans existing deploy history from the renamed Single.
	if frappe.db.table_exists("Deploy Log"):
		frappe.db.sql(
			"""
			UPDATE `tabDeploy Log`
			SET parent = 'Deploy Center'
			WHERE parent = 'Publisher' AND parenttype = 'Deploy Center'
			"""
		)
