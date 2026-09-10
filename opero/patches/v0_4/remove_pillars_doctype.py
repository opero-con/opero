"""Move the legacy Pillars singleton into Our Work expertise and remove it."""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.exists("DocType", "Pillars"):
		return
	if frappe.db.exists("DocType", "Our Work"):
		current = frappe.get_single("Our Work")
		legacy_rows = frappe.db.sql(
			"SELECT title, description FROM `tabPillar` WHERE parent = %s ORDER BY idx",
			"Pillars",
			as_dict=True,
		)
		if not current.expertise and legacy_rows:
			for row in legacy_rows:
				current.append("expertise", row)
			current.save(ignore_permissions=True)
	frappe.db.delete("DocType", "Pillars")
	frappe.db.delete("Singles", {"doctype": "Pillars"})
	frappe.db.sql("DELETE FROM `tabPillar` WHERE parent = %s", "Pillars")
