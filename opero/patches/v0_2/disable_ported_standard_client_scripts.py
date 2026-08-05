"""Disable Client Scripts whose logic now lives in opero/public/js/custom/."""

from __future__ import annotations

import frappe

PORTED_CLIENT_SCRIPTS = [
	"Auto Height Note: TS",
	"Budget Line Filter",
	"Costing & Margin Hide",
	"Days to Hours",
	"Mileage Section Visibility",
	"Nights in Travel Request",
	"Per Diem & Mileage Claim Calculations",
	"Project Fetch to Material Request Item",
	"TS: Auto-fill Project Info and Sync Activity Type (Safe for Submit)",
	"Time_allocation_handler",
	"Total Spent Hrs",
	"Update task_end in TTD",
	"personnel default and banner",
]


def execute():
	for name in PORTED_CLIENT_SCRIPTS:
		if frappe.db.exists("Client Script", name):
			frappe.db.set_value("Client Script", name, "enabled", 0, update_modified=False)
