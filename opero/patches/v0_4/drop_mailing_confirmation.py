"""Drop confirmation requests; members are active until they unsubscribe."""

import frappe


FIELD_NAME = "Email Group Member-custom_confirmation_status"


def execute():
	_drop_confirmation_status_field()
	for doctype in ("Mailing Confirmation Request", "Mailing Confirmation Item"):
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)
	from opero.mailing.membership import sync_email

	for email in set(frappe.get_all("Email Group Member", pluck="email")):
		sync_email(email)
	frappe.clear_cache()


def _drop_confirmation_status_field():
	if frappe.db.exists("Custom Field", FIELD_NAME):
		frappe.delete_doc("Custom Field", FIELD_NAME, ignore_permissions=True, force=True)
	for property_setter_name in frappe.get_all(
		"Property Setter",
		filters={"doc_type": "Email Group Member", "field_name": "custom_confirmation_status"},
		pluck="name",
	):
		frappe.delete_doc("Property Setter", property_setter_name, ignore_permissions=True, force=True)
	columns = set(frappe.db.get_table_columns("Email Group Member"))
	if "custom_confirmation_status" in columns:
		frappe.db.sql_ddl("alter table `tabEmail Group Member` drop column `custom_confirmation_status`")
	frappe.clear_cache(doctype="Email Group Member")
