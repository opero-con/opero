from __future__ import annotations

import json

import frappe


CHART_NAME = "ToDo Created vs Closed (30d)"


def execute():
	rows = frappe.get_all(
		"Dashboard Settings",
		filters={"chart_config": ("is", "set")},
		fields=["name", "chart_config"],
		limit_page_length=0,
	)

	for row in rows:
		config = frappe.parse_json(row.chart_config) or {}
		chart_config = config.get(CHART_NAME)
		if not isinstance(chart_config, dict):
			continue

		filters = chart_config.get("filters")
		if not isinstance(filters, dict):
			continue

		changed = False
		for key in ("from_date", "to_date"):
			if key in filters:
				filters.pop(key, None)
				changed = True

		if changed:
			chart_config["filters"] = filters
			config[CHART_NAME] = chart_config
			frappe.db.set_value(
				"Dashboard Settings",
				row.name,
				"chart_config",
				json.dumps(config, separators=(",", ":")),
			)
