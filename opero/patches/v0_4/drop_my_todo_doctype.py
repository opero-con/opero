"""Drop the legacy My ToDo single doctype; Flow Hub replaces it."""

import frappe


def execute():
	if frappe.db.exists("Client Script", "ToDo List") and frappe.db.get_value(
		"Client Script", "ToDo List", "dt"
	) == "My ToDo":
		frappe.delete_doc("Client Script", "ToDo List", force=True, ignore_permissions=True)

	if frappe.db.exists("DocType", "My ToDo"):
		frappe.delete_doc("DocType", "My ToDo", force=True, ignore_permissions=True)

	frappe.clear_cache()
