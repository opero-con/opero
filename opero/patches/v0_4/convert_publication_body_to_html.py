from types import SimpleNamespace

import frappe

from opero.opero_site.body_html import body_sections_to_html
from opero.opero_site.utils import body_sections


def execute():
	frappe.reload_doc("opero_site", "doctype", "publication")
	if not frappe.db.has_column("Publication", "body"):
		return
	if not frappe.db.table_exists("Body Section"):
		return

	parents = frappe.db.sql(
		"""
		SELECT DISTINCT parent
		FROM `tabBody Section`
		WHERE parenttype = 'Publication' AND parentfield = 'body'
		"""
	)
	for (parent,) in parents:
		rows = frappe.db.sql(
			"""
			SELECT heading, paragraphs, bullets, links
			FROM `tabBody Section`
			WHERE parent = %s AND parenttype = 'Publication' AND parentfield = 'body'
			ORDER BY idx
			""",
			parent,
			as_dict=True,
		)
		html = body_sections_to_html(body_sections([SimpleNamespace(**row) for row in rows]))
		frappe.db.set_value("Publication", parent, "body", html, update_modified=False)

	frappe.db.sql(
		"""
		DELETE FROM `tabBody Section`
		WHERE parenttype = 'Publication' AND parentfield = 'body'
		"""
	)
