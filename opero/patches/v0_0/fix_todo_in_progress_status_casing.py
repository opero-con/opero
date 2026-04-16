from __future__ import annotations

"""Fix 'In progress' → 'In Progress' in the ToDo status Property Setter and
backfill any existing records that were saved with the lowercase variant."""

import frappe

OLD_VALUE = "Open\nIn progress\nClosed\nCancelled"
NEW_VALUE = "Open\nIn Progress\nClosed\nCancelled"

PROPERTY_SETTER_FILTERS = {
	"doctype_or_field": "DocField",
	"doc_type": "ToDo",
	"field_name": "status",
	"property": "options",
}


def execute():
	# Fix the Property Setter
	ps_name = frappe.db.exists("Property Setter", PROPERTY_SETTER_FILTERS)
	if ps_name:
		current = frappe.db.get_value("Property Setter", ps_name, "value")
		if current == OLD_VALUE:
			frappe.db.set_value(
				"Property Setter",
				ps_name,
				"value",
				NEW_VALUE,
				update_modified=False,
			)

	# Backfill any records saved with the old lowercase value
	frappe.db.sql(
		"UPDATE `tabToDo` SET status = 'In Progress' WHERE status = 'In progress'"
	)

	frappe.clear_cache(doctype="ToDo")
