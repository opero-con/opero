"""Drop Enterprise naming_series; IDs are E + five random digits via script."""

import frappe


def execute():
	frappe.reload_doc("opero", "doctype", "enterprise")
	for property_setter_name in frappe.get_all(
		"Property Setter",
		filters={"doc_type": "Enterprise", "field_name": "naming_series"},
		pluck="name",
	):
		frappe.delete_doc("Property Setter", property_setter_name, ignore_permissions=True, force=True)
	columns = set(frappe.db.get_table_columns("Enterprise"))
	if "naming_series" in columns:
		frappe.db.sql_ddl("alter table `tabEnterprise` drop column `naming_series`")
	# Stale Series option left from ENT-.YYYY.- naming.
	if frappe.db.exists("Series", "ENT-"):
		frappe.db.sql("delete from `tabSeries` where name=%s", "ENT-")
	frappe.clear_cache(doctype="Enterprise")
