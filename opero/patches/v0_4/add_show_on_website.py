import frappe

DOCTYPES = ("Publication", "Team Member")
SINGLES = ("Home Page", "Privacy", "Site Settings")
ON_SITE = ("To publish", "Published")


def execute():
	for doctype in ("publication", "team_member", "home_page", "privacy", "site_settings"):
		frappe.reload_doc("opero_site", "doctype", doctype)

	for doctype in DOCTYPES:
		if not frappe.db.table_exists(doctype) or not frappe.db.has_column(doctype, "show_on_website"):
			continue
		frappe.db.sql(
			f"""
			UPDATE `tab{doctype}`
			SET show_on_website = CASE
				WHEN status IN ('To publish', 'Published') THEN 1
				ELSE 0
			END
			"""
		)

	for name in SINGLES:
		if not frappe.db.exists("DocType", name):
			continue
		status = frappe.db.get_single_value(name, "status")
		frappe.db.set_value(
			name,
			name,
			"show_on_website",
			1 if status in ON_SITE else 0,
			update_modified=False,
		)
