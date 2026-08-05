"""Project manager lookup API."""

from __future__ import annotations

import frappe


@frappe.whitelist()
def get_project_master_managers():
	return frappe.db.sql(
		"""
		SELECT u.name, u.first_name
		FROM `tabUser` u
		JOIN `tabHas Role` hr ON hr.parent = u.name
		WHERE hr.role = %s AND u.enabled = 1
		GROUP BY u.name
		ORDER BY u.first_name
		LIMIT 2
		""",
		("Projects Master Manager",),
		as_dict=True,
	)
