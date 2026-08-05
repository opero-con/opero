"""HR Settings handlers ported from FC Server Scripts."""

from __future__ import annotations

import frappe


def on_update_hr_settings(doc, _method=None):
	standard_working_hours = float(
		frappe.db.get_single_value("HR Settings", "standard_working_hours") or 0
	)
	rows = frappe.get_all("Distribution Detail", fields=["name", "parent", "available_days"])
	for row in rows:
		available_days = float(row.available_days or 0)
		frappe.db.set_value(
			"Distribution Detail",
			row.name,
			{
				"standard_working_hours": standard_working_hours,
				"available_hours": available_days * standard_working_hours,
			},
			update_modified=False,
		)
		if row.parent:
			frappe.db.set_value(
				"Work Hours Summary",
				row.parent,
				"working_hours",
				standard_working_hours,
				update_modified=False,
			)
