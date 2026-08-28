import frappe

DOCTYPES = ("Publication", "Team Member")
SINGLES = ("Home Page", "Privacy", "Site Settings")
RENAMES = {
	"Published": "To publish",
	"Unpublished": "To unpublish",
}


def execute():
	for doctype in DOCTYPES:
		if not frappe.db.table_exists(doctype) or not frappe.db.has_column(doctype, "status"):
			continue
		for old, new in RENAMES.items():
			frappe.db.sql(
				f"UPDATE `tab{doctype}` SET status = %s WHERE status = %s",
				(new, old),
			)

	for name in SINGLES:
		if not frappe.db.exists("DocType", name):
			continue
		current = frappe.db.get_single_value(name, "status")
		if current in RENAMES:
			frappe.db.set_value(name, name, "status", RENAMES[current], update_modified=False)
