"""Adopt FC custom Script Reports as standard Opero module reports."""

from __future__ import annotations

import frappe


REPORTS = ("Dynamic Timesheet", "Used Hrs Summary")


def execute():
	for name in REPORTS:
		if not frappe.db.exists("Report", name):
			continue
		frappe.db.set_value(
			"Report",
			name,
			{
				"is_standard": "Yes",
				"module": "Opero",
				"report_script": None,
				"disabled": 0,
			},
			update_modified=False,
		)
