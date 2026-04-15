from __future__ import annotations

import frappe

OLD_NAME = "ToDo Created vs Closed 30d"
NEW_NAME = "ToDo Created vs Closed"


def execute():
	# Fix workspace link rows that still reference the old report name
	frappe.db.sql(
		"""
			UPDATE `tabWorkspace Link`
			SET link_to = %s,
			    label   = CASE WHEN label = %s THEN %s ELSE label END
			WHERE link_to = %s
		""",
		[NEW_NAME, OLD_NAME, NEW_NAME, OLD_NAME],
	)

	# Fix workspace shortcut rows
	frappe.db.sql(
		"""
			UPDATE `tabWorkspace Shortcut`
			SET link_to = %s,
			    label   = CASE WHEN label = %s THEN %s ELSE label END
			WHERE link_to = %s
		""",
		[NEW_NAME, OLD_NAME, NEW_NAME, OLD_NAME],
	)

	frappe.clear_cache(doctype="Workspace")
