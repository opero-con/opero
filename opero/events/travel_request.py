"""Travel Request event handlers ported from FC Server Scripts."""

from __future__ import annotations

import frappe


def validate_travel_request(doc, _method=None):
	if doc.is_new():
		return
	doc.custom_previous_workflow_state = frappe.db.get_value(
		"Travel Request", doc.name, "workflow_state"
	)
