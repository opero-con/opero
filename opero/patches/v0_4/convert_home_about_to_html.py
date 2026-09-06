"""Convert Home Page about paragraphs from the Paragraph child table to Text Editor HTML."""

from __future__ import annotations

import frappe

from opero.opero_site.body_html import paragraphs_to_html


def execute():
	frappe.reload_doc("opero_site", "doctype", "home_page")
	if not frappe.get_meta("Home Page").has_field("about_body"):
		return
	if not frappe.db.table_exists("Paragraph"):
		return

	rows = frappe.db.sql(
		"""
		SELECT paragraph
		FROM `tabParagraph`
		WHERE parenttype = 'Home Page' AND parentfield = 'about_paragraphs'
		ORDER BY idx
		""",
		as_dict=True,
	)
	if rows:
		html = paragraphs_to_html([row.paragraph for row in rows])
		frappe.db.set_single_value("Home Page", "about_body", html, update_modified=False)

	frappe.db.sql(
		"""
		DELETE FROM `tabParagraph`
		WHERE parenttype = 'Home Page' AND parentfield = 'about_paragraphs'
		"""
	)

	if frappe.db.exists("DocType", "Paragraph") and not frappe.db.sql(
		"SELECT name FROM `tabParagraph` LIMIT 1"
	):
		frappe.delete_doc("DocType", "Paragraph", force=1, ignore_permissions=True)
