"""Free the singular Impact name for the homepage section Single."""

from __future__ import annotations

import frappe


def execute():
	# Impact was the child table before the homepage section became singular.
	if frappe.db.exists("DocType", "Impact") and frappe.db.get_value("DocType", "Impact", "istable"):
		frappe.rename_doc("DocType", "Impact", "Impact Metric", force=True)

	if frappe.db.exists("DocType", "Impacts"):
		frappe.rename_doc("DocType", "Impacts", "Impact", force=True)
		# frappe.rename_doc fixes parenttype for the Single's child rows but not
		# parent, since a Single's document name equals its doctype name.
		frappe.db.sql(
			"""
			UPDATE `tabImpact Metric`
			SET parent = 'Impact'
			WHERE parent = 'Impacts' AND parenttype = 'Impact'
			"""
		)

	frappe.db.sql(
		"""
		UPDATE `tabWorkspace Link`
		SET label = 'Impact'
		WHERE link_to = 'Impact' AND label = 'Impacts' AND link_type = 'DocType'
		"""
	)
