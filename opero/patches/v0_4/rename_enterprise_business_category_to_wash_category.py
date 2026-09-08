import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doc("opero", "doctype", "enterprise")
	if frappe.db.has_column("Enterprise", "business_category"):
		if frappe.db.has_column("Enterprise", "wash_category"):
			# DocType sync already added the new column; copy then drop the old one.
			frappe.db.sql(
				"""
				update `tabEnterprise`
				set wash_category = business_category
				where ifnull(wash_category, '') = '' and ifnull(business_category, '') != ''
				"""
			)
			frappe.db.sql_ddl("alter table `tabEnterprise` drop column `business_category`")
		else:
			rename_field("Enterprise", "business_category", "wash_category")
	frappe.clear_cache(doctype="Enterprise")
