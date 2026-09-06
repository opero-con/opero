import frappe

from opero.opero_site.body_html import normalize_body_html


def execute():
	frappe.reload_doc("opero_site", "doctype", "privacy")
	if not frappe.get_meta("Privacy").has_field("body"):
		return
	body = frappe.db.get_single_value("Privacy", "body")
	if not body:
		return
	normalized = normalize_body_html(body)
	if normalized != body:
		frappe.db.set_single_value("Privacy", "body", normalized, update_modified=False)
