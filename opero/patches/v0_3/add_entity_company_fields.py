"""Give project-scoped standard DocTypes a company, so they can be entity-scoped.

Task, Timesheet, Travel Request, Expense Claim and Material Request already ship
with a `company` field. Activity Type and Activity Cost — Opero's project rate
factors — do not, so they get one here.
"""

from __future__ import annotations

import json
from pathlib import Path

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	payload_path = Path(__file__).with_name("entity_company_custom_fields.json")
	rows = json.loads(payload_path.read_text())

	by_dt: dict[str, list[dict]] = {}
	for row in rows:
		doctype = row.pop("dt")
		if not frappe.db.exists("DocType", doctype):
			continue
		by_dt.setdefault(doctype, []).append({**row, "module": "Opero"})

	if by_dt:
		create_custom_fields(by_dt, update=True)
