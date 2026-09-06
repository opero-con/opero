from types import SimpleNamespace

import frappe

from opero.opero_site.body_html import body_sections_to_html
from opero.opero_site.utils import body_sections


def execute():
	frappe.reload_doc("opero_site", "doctype", "privacy")
	if not frappe.get_meta("Privacy").has_field("body"):
		return
	if not frappe.db.table_exists("Body Section"):
		return

	rows = frappe.db.sql(
		"""
		SELECT heading, paragraphs, bullets, links
		FROM `tabBody Section`
		WHERE parenttype = 'Privacy' AND parentfield = 'sections'
		ORDER BY idx
		""",
		as_dict=True,
	)
	if rows:
		html = body_sections_to_html(body_sections([SimpleNamespace(**row) for row in rows]))
		frappe.db.set_single_value("Privacy", "body", html, update_modified=False)

	frappe.db.sql(
		"""
		DELETE FROM `tabBody Section`
		WHERE parenttype = 'Privacy' AND parentfield = 'sections'
		"""
	)

	if frappe.db.exists("DocType", "Body Section") and not frappe.db.sql(
		"SELECT name FROM `tabBody Section` LIMIT 1"
	):
		frappe.delete_doc("DocType", "Body Section", force=1, ignore_permissions=True)
