"""Create Project/Task/Timesheet/ToDo custom fields used by ported FC scripts.

Applied via patch (not fixtures) so sites without HRMS Travel Request still sync
Zoho Custom Field fixtures from hooks.
"""

from __future__ import annotations

import json
from pathlib import Path

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	payload_path = Path(__file__).with_name("standard_doctype_custom_fields.json")
	rows = json.loads(payload_path.read_text())

	by_dt = {}
	for row in rows:
		dt = row["dt"]
		if not frappe.db.exists("DocType", dt):
			continue
		field = {
			"fieldname": row["fieldname"],
			"label": row.get("label"),
			"fieldtype": row["fieldtype"],
			"insert_after": row.get("insert_after"),
			"options": row.get("options"),
			"reqd": row.get("reqd") or 0,
			"read_only": row.get("read_only") or 0,
			"hidden": row.get("hidden") or 0,
			"no_copy": row.get("no_copy") or 0,
			"allow_on_submit": row.get("allow_on_submit") or 0,
			"in_list_view": row.get("in_list_view") or 0,
			"in_standard_filter": row.get("in_standard_filter") or 0,
			"default": row.get("default"),
			"precision": row.get("precision"),
			"description": row.get("description"),
			"depends_on": row.get("depends_on"),
			"mandatory_depends_on": row.get("mandatory_depends_on"),
			"read_only_depends_on": row.get("read_only_depends_on"),
			"collapsible": row.get("collapsible") or 0,
			"fetch_from": row.get("fetch_from"),
			"fetch_if_empty": row.get("fetch_if_empty") or 0,
			"translatable": row.get("translatable") or 0,
			"module": "Opero",
		}
		by_dt.setdefault(dt, []).append({k: v for k, v in field.items() if v not in (None, "")})

	if by_dt:
		create_custom_fields(by_dt, update=True)
