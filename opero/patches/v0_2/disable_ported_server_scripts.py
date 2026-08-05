"""Disable Server Scripts whose logic now lives in Opero Python modules."""

from __future__ import annotations

import frappe

PORTED_SERVER_SCRIPTS = [
	"Allocated Hrs Fetch and Throw",
	"Anti Spill",
	"Auto Share Records",
	"Available Hrs",
	"Chart in Project Budget",
	"Custom_Title",
	"Full Name",
	"Get Project Master Managers",
	"Holidays Fetch",
	"Missing Project Rate Factor",
	"Non PM Restriction",
	"PM Email Fetch",
	"Previous Workflow State",
	"Sum of Allocated Hrs in Project",
	"TTD Update",
	"Time dist. listen to working hrs",
	"ToDo AutoShare upon Mention",
	"ToDo Email Notification",
	"on_update push to TTD",
	"on_update pust start to TDD",
]


def execute():
	for name in PORTED_SERVER_SCRIPTS:
		if frappe.db.exists("Server Script", name):
			frappe.db.set_value("Server Script", name, "disabled", 1, update_modified=False)
