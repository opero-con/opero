"""Rename the legacy publisher role profile without changing its membership."""

import frappe
from frappe.model.rename_doc import rename_doc


def execute():
	if frappe.db.exists("Role Profile", "Website Publication Publisher"):
		rename_doc("Role Profile", "Website Publication Publisher", "Blogger", ignore_permissions=True)
	if frappe.db.exists("Role Profile", "Blogger"):
		frappe.db.set_value("Role Profile", "Blogger", "role_profile", "Blogger")
		frappe.clear_cache()
