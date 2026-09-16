import json

import frappe


def execute():
	chart = frappe.db.exists("Dashboard Chart", "ToDo In Progress Aging")
	if chart:
		frappe.db.set_value(
			"Dashboard Chart",
			chart,
			"filters_json",
			json.dumps({"min_days": 0}),
			update_modified=False,
		)
