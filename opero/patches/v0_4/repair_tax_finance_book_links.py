"""Repair Finance Book links left behind by a partial Statutory-to-Tax rename."""

import frappe
from frappe.model.rename_doc import get_link_fields, rename_dynamic_links, update_link_field_values


def execute():
	if frappe.db.exists("Finance Book", "Statutory"):
		return
	if frappe.db.get_value("Finance Book", "Tax", "finance_book_name") != "Statutory":
		return

	# The master ID was changed outside Frappe's rename flow. Use its link
	# helpers to include child tables, submitted documents and ledger entries.
	update_link_field_values(get_link_fields("Finance Book"), "Statutory", "Tax", "Finance Book")
	rename_dynamic_links("Finance Book", "Statutory", "Tax")
	frappe.db.set_value("Finance Book", "Tax", "finance_book_name", "Tax", update_modified=False)
	frappe.clear_cache()
