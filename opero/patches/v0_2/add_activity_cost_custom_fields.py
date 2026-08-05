"""Create Activity Cost custom fields used by Day Rate Conversion client JS."""

from __future__ import annotations

import json
from pathlib import Path

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	if not frappe.db.exists("DocType", "Activity Cost"):
		return

	payload_path = Path(__file__).with_name("activity_cost_custom_fields.json")
	rows = json.loads(payload_path.read_text())

	by_dt = {}
	for row in rows:
		field = {
			"fieldname": row["fieldname"],
			"label": row.get("label"),
			"fieldtype": row["fieldtype"],
			"insert_after": row.get("insert_after"),
			"options": row.get("options"),
			"depends_on": row.get("depends_on"),
			"collapsible": row.get("collapsible") or 0,
			"module": "Opero",
		}
		by_dt.setdefault(row["dt"], []).append(
			{k: v for k, v in field.items() if v not in (None, "")}
		)

	create_custom_fields(by_dt, update=True)
