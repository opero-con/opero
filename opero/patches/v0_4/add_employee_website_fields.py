"""Add Opero's public team profile fields to Employee."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	had_use_employee_image = bool(
		frappe.db.exists("Custom Field", {"dt": "Employee", "fieldname": "use_employee_image"})
	)
	for fieldname in (
		"wash_personnel",
		"member_name",
		"portrait_alt",
		"portrait_position",
		"portrait_scale",
		"portrait_hover_scale",
		"website_portrait_column",
		"custom_column_break_ldtja",
		"custom_column_break_sqxow",
		"custom_section_break_cr5tu",
	):
		obsolete = frappe.db.exists("Custom Field", {"dt": "Employee", "fieldname": fieldname})
		if obsolete:
			frappe.delete_doc("Custom Field", obsolete, force=True, ignore_permissions=True)
	create_custom_fields(
		{
			"Employee": [
				{"fieldname": "opero_website_tab", "fieldtype": "Tab Break", "label": "Website", "insert_after": "old_parent"},
				{"fieldname": "website_profile_section", "fieldtype": "Section Break", "label": "Website profile", "insert_after": "opero_website_tab"},
				{"fieldname": "show_on_website", "fieldtype": "Check", "label": "Show on website", "insert_after": "website_profile_section"},
				{"fieldname": "role", "fieldtype": "Data", "label": "Role", "insert_after": "show_on_website"},
				{"fieldname": "slug", "fieldtype": "Data", "label": "Slug", "unique": 1, "hidden": 1, "read_only": 1, "insert_after": "role"},
				{"fieldname": "website_order_column", "fieldtype": "Column Break", "insert_after": "slug"},
				{"fieldname": "sort_order", "fieldtype": "Int", "label": "Order", "default": "10", "insert_after": "website_order_column"},
				{"fieldname": "website_status", "fieldtype": "Select", "label": "Website status", "read_only": 1,
				 "options": "Draft\nTo deploy\nPublished\nTo unpublish\nUnpublished", "default": "Draft", "insert_after": "sort_order"},
				{"fieldname": "website_portrait_section", "fieldtype": "Section Break", "label": "Portrait", "insert_after": "website_status"},
				{"fieldname": "use_employee_image", "fieldtype": "Check", "label": "Use employee image", "default": "1", "insert_after": "website_portrait_section"},
				{"fieldname": "portrait", "fieldtype": "Attach Image", "label": "Portrait", "depends_on": "eval:!doc.use_employee_image", "insert_after": "use_employee_image"},
				{"fieldname": "website_links_section", "fieldtype": "Section Break", "label": "Links", "insert_after": "portrait"},
				{"fieldname": "linkedin", "fieldtype": "Data", "label": "LinkedIn URL", "options": "URL", "insert_after": "website_links_section"},
			],
		},
		update=True,
	)
	if not had_use_employee_image:
		frappe.db.sql(
			"UPDATE `tabEmployee` SET use_employee_image = 0 WHERE IFNULL(portrait, '') != ''"
		)
	frappe.clear_cache(doctype="Employee")
