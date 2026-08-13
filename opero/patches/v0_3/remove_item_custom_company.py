"""Drop Item.custom_company so Company User Permissions no longer block Item create.

The field came in with the FC site-config import. Opero never scoped Item by
entity, and a parent Company link on Item makes leftover Company User Permission
rows deny create even when the user has Item Manager.
"""

from __future__ import annotations

import json

import frappe

FIELD_NAME = "Item-custom_company"
FIELD_ORDER_SETTER = "Item-main-field_order"


def execute():
	if frappe.db.exists("Custom Field", FIELD_NAME):
		frappe.delete_doc("Custom Field", FIELD_NAME, ignore_permissions=True, force=True)

	if frappe.db.exists("Property Setter", FIELD_ORDER_SETTER):
		value = frappe.db.get_value("Property Setter", FIELD_ORDER_SETTER, "value")
		if value and "custom_company" in value:
			try:
				order = json.loads(value)
			except json.JSONDecodeError:
				order = None
			if isinstance(order, list):
				frappe.db.set_value(
					"Property Setter",
					FIELD_ORDER_SETTER,
					"value",
					json.dumps([field for field in order if field != "custom_company"]),
				)

	frappe.clear_cache(doctype="Item")
