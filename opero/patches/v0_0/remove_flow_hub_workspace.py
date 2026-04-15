from __future__ import annotations

"""Remove the Flow Hub workspace — it shadows the flow-hub Page route.
The Page itself is the entry point; no wrapper workspace is needed.
"""

import frappe

WORKSPACE_NAME = "Flow Hub"


def execute():
	if frappe.db.exists("Workspace", WORKSPACE_NAME):
		frappe.delete_doc("Workspace", WORKSPACE_NAME, ignore_permissions=True, force=True)
		frappe.clear_cache(doctype="Workspace")
