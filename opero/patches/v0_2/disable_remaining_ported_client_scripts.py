"""Disable leftover Client Scripts whose logic now lives in opero/public/js/custom/."""

from __future__ import annotations

import frappe

PORTED_CLIENT_SCRIPTS = [
	"Auto Submit LA if Approved",
	"Day Rate Conversion",
	"Description on Resource Planner with Project Filter",
	"Drill-Down",
	"Item naming series",
	"Name Autohide",
]


def execute():
	for name in PORTED_CLIENT_SCRIPTS:
		if frappe.db.exists("Client Script", name):
			frappe.db.set_value("Client Script", name, "enabled", 0, update_modified=False)
