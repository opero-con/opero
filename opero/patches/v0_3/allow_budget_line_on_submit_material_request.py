"""Allow Budget Line edits on submitted Material Requests.

`import_fc_site_config` only upserts once, so flipping allow_on_submit in
`data/fc_site_config/custom_field.json` does not reach sites where that patch
already ran. This does.
"""

from __future__ import annotations

import frappe

FIELD_NAME = "Material Request Item-custom_budget_line"


def execute():
	if not frappe.db.exists("Custom Field", FIELD_NAME):
		return

	frappe.db.set_value("Custom Field", FIELD_NAME, "allow_on_submit", 1)
	frappe.clear_cache(doctype="Material Request Item")
