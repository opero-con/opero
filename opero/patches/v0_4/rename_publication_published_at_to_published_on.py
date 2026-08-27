import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doc("opero_site", "doctype", "publication")

	if frappe.db.has_column("Publication", "published_at"):
		rename_field("Publication", "published_at", "published_on")
