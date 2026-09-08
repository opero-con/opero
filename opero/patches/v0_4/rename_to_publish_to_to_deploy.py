import frappe

from opero.opero_site.publish_status import publish_status_field

DOCTYPES = ("Publication", "Team Member", "Enterprise")
SINGLES = ("Home Page", "Privacy policy", "Site Settings")


def execute():
	for doctype in DOCTYPES:
		if not frappe.db.table_exists(doctype):
			continue
		field = publish_status_field(doctype)
		if not frappe.db.has_column(doctype, field):
			continue
		frappe.db.sql(
			f"UPDATE `tab{doctype}` SET `{field}` = %s WHERE `{field}` = %s",
			("To deploy", "To publish"),
		)

	for name in SINGLES:
		if not frappe.db.exists("DocType", name):
			continue
		if frappe.db.get_single_value(name, "status") == "To publish":
			frappe.db.set_value(name, name, "status", "To deploy", update_modified=False)
