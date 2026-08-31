"""Let Website Manager read and close website Communications."""

from __future__ import annotations

import frappe
from frappe.permissions import add_permission, update_permission_property


def execute():
	if not frappe.db.exists(
		"Custom DocPerm",
		{"parent": "Communication", "role": "Website Manager", "permlevel": 0, "if_owner": 0},
	):
		add_permission("Communication", "Website Manager", 0, "read")
	update_permission_property("Communication", "Website Manager", 0, "read", 1)
	update_permission_property("Communication", "Website Manager", 0, "write", 1)
