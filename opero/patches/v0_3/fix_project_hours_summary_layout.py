"""Put the Hours HTML summary first in its section at full width.

`custom_hours_summary` was created with insert_after the section break, but the
site field_order property setter never listed it, so the form parked it in a
narrow column beside the (hidden) metric fields and the label wrapped.
"""

from __future__ import annotations

import json

import frappe

HOURS_FIELDS = [
	"custom_section_break_fdfzy",
	"custom_hours_summary",
	"custom_column_break_eszdr",
	"custom_allocated_hours",
	"custom_column_break_h6iui",
	"actual_time",
	"custom_column_break_y80wz",
	"custom_percent_progress",
]


def execute():
	if frappe.db.exists("Custom Field", "Project-custom_hours_summary"):
		frappe.db.set_value(
			"Custom Field",
			"Project-custom_hours_summary",
			"insert_after",
			"custom_section_break_fdfzy",
		)
	_reorder_hours_in_field_order()
	frappe.clear_cache(doctype="Project")


def _reorder_hours_in_field_order() -> None:
	name = "Project-main-field_order"
	current = frappe.db.get_value("Property Setter", name, "value")
	if not current:
		return

	order = json.loads(current)
	# Drop the hours block (and a stray summary if present), then re-insert it
	# as a single contiguous group starting at the Hours section break.
	without = [f for f in order if f not in HOURS_FIELDS]
	anchor = len(without)
	if "percent_complete" in without:
		anchor = without.index("percent_complete") + 1
	elif "custom_section_break_rttw7" in without:
		anchor = without.index("custom_section_break_rttw7")
	fixed = without[:anchor] + HOURS_FIELDS + without[anchor:]

	frappe.db.set_value("Property Setter", name, "value", json.dumps(fixed))
