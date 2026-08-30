"""Home Page, Privacy, and Site Settings stay on-site; drop Show on website."""

from __future__ import annotations

import frappe

from opero.opero_site.publish_status import ALWAYS_ON_SITE, PUBLISHED, TO_PUBLISH


def execute():
	for doctype in ("home_page", "privacy", "site_settings"):
		frappe.reload_doc("opero_site", "doctype", doctype)

	for name in ALWAYS_ON_SITE:
		if not frappe.db.exists("DocType", name):
			continue
		frappe.db.delete("Singles", {"doctype": name, "field": "show_on_website"})
		custom_field = frappe.db.exists("Custom Field", {"dt": name, "fieldname": "show_on_website"})
		if custom_field:
			frappe.delete_doc("Custom Field", custom_field, ignore_permissions=True, force=True)
		for property_setter_name in frappe.get_all(
			"Property Setter",
			filters={"doc_type": name, "field_name": "show_on_website"},
			pluck="name",
		):
			frappe.delete_doc(
				"Property Setter", property_setter_name, ignore_permissions=True, force=True
			)
		if frappe.db.get_single_value(name, "status") == PUBLISHED:
			continue
		frappe.db.set_value(name, name, "status", TO_PUBLISH, update_modified=False)
		frappe.clear_cache(doctype=name)
