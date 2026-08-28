import frappe


def execute():
	if not frappe.db.table_exists("Publication"):
		return
	if not frappe.db.has_column("Publication", "publication_type"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabPublication`
		SET publication_type = 'Overview'
		WHERE publication_type = 'Portfolio'
		"""
	)
