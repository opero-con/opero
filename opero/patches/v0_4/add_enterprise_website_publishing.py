import frappe

CRM_STATUSES = ("Identified", "Onboarded", "Active Support", "Graduated", "Dormant")
WEBSITE_STATUSES = ("Draft", "To deploy", "To publish", "Published", "To unpublish", "Unpublished")


def _in_list(values: tuple[str, ...]) -> tuple[str, tuple]:
	placeholders = ", ".join(["%s"] * len(values))
	return placeholders, values


def execute():
	"""Keep CRM Status as `status`; website publish sync uses `website_status`."""
	if not frappe.db.table_exists("Enterprise"):
		return

	columns = set(frappe.db.get_table_columns("Enterprise"))
	web_ph, web_vals = _in_list(WEBSITE_STATUSES)

	# Prior branch state: CRM in enterprise_status, website sync in status.
	if "enterprise_status" in columns:
		if "website_status" not in columns:
			frappe.db.sql_ddl(
				"ALTER TABLE `tabEnterprise` ADD COLUMN `website_status` varchar(140) DEFAULT 'Draft'"
			)
		frappe.db.sql(
			f"""
			UPDATE `tabEnterprise`
			SET website_status = status
			WHERE status IN ({web_ph})
			""",
			web_vals,
		)
		frappe.db.sql(
			"""
			UPDATE `tabEnterprise`
			SET status = enterprise_status
			WHERE IFNULL(enterprise_status, '') != ''
			"""
		)
		frappe.db.sql(
			f"""
			UPDATE `tabEnterprise`
			SET status = 'Identified'
			WHERE status IN ({web_ph}) OR IFNULL(status, '') = ''
			""",
			web_vals,
		)
		frappe.db.sql_ddl("ALTER TABLE `tabEnterprise` DROP COLUMN `enterprise_status`")
	elif "website_status" not in columns:
		# CRM-only status column: add website_status without touching Identified/...
		frappe.db.sql_ddl(
			"ALTER TABLE `tabEnterprise` ADD COLUMN `website_status` varchar(140) DEFAULT 'Draft'"
		)
		frappe.db.sql("UPDATE `tabEnterprise` SET website_status = 'Draft'")
		frappe.db.sql(
			f"""
			UPDATE `tabEnterprise`
			SET status = 'Identified'
			WHERE status IN ({web_ph}) OR IFNULL(status, '') = ''
			""",
			web_vals,
		)

	frappe.reload_doc("opero", "doctype", "enterprise")
	if frappe.db.has_column("Enterprise", "slug"):
		frappe.db.sql_ddl("ALTER TABLE `tabEnterprise` DROP COLUMN `slug`")
	frappe.reload_doc("opero_site", "workspace", "opero_website")
	frappe.clear_cache(doctype="Enterprise")
