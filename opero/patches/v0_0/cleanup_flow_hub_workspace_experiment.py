from __future__ import annotations

"""Clean up DB records left by the Flow Hub workspace experiment.

Removes the 'Flow Hub' workspace and the orphaned 'opero-flow-hub' page
that were created during the sidebar experiment. The page reverts to its
original name 'flow-hub' via the standard JSON fixture on next migrate.
"""

import frappe


def execute():
	for workspace in ("Flow Hub",):
		if frappe.db.exists("Workspace", workspace):
			frappe.delete_doc("Workspace", workspace, ignore_permissions=True, force=True)

	if frappe.db.exists("Page", "opero-flow-hub"):
		frappe.delete_doc("Page", "opero-flow-hub", ignore_permissions=True, force=True)

	frappe.clear_cache(doctype="Workspace")
	frappe.clear_cache(doctype="Page")
