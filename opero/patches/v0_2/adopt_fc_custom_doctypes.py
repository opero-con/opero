"""Mark FC-imported DocTypes as standard Opero DocTypes and disable ported Client Scripts.

On Frappe Cloud these DocTypes already exist with custom=1. After the app
ships the same DocTypes as module files, clear custom so Desk treats them as
app-owned. Also disable Client Scripts whose logic now lives in public/js.
"""

from __future__ import annotations

import frappe

FC_DOCTYPES = [
	"Accomodation",
	"Actual Spend",
	"Budget Line",
	"Cash Advance-Reimbursable Form",
	"Consultant Task",
	"Contract Documents",
	"Distribution Detail",
	"Enterprise",
	"Expense Classification",
	"My ToDo",
	"Per Diem Costing",
	"Project Budget",
	"Project Budget Items",
	"Project Time Allocation",
	"Task Time Allocation",
	"Task Time Distribution",
	"Task Time Distribution Spread",
	"Time Allocation Detail",
	"WaSH Category",
	"WaSH Competency Category",
	"WaSH Expert Profile",
	"WaSH Expertise Area",
	"WaSH Personnel",
	"Work Hours Summary",
]

PORTED_CLIENT_SCRIPTS = [
	"Child Table",
	"Calculations",
	"Currency",
	"Date & Personnel Autofill",
	"Self Approval Warning by Call to Server Script",
	"Auto Resize",
	"Hide Completion Field",
	"ToDo List",
	"Chart in Project Budget",
	"Completed On Compulsory",
	"Days",
	"Hours",
	"Project Task",
	"field population and total distribution",
	"Re-Distribute Month(s)",
	"TTDS Days to Hrs",
	"Subcategory Options",
	"Filter",
	"New Contact Button",
	"Autopopulate Months",
]


def execute():
	for name in FC_DOCTYPES:
		if not frappe.db.exists("DocType", name):
			continue
		frappe.db.set_value("DocType", name, "custom", 0, update_modified=False)
		frappe.db.set_value("DocType", name, "module", "Opero", update_modified=False)

	for name in PORTED_CLIENT_SCRIPTS:
		if frappe.db.exists("Client Script", name):
			frappe.db.set_value("Client Script", name, "enabled", 0, update_modified=False)
