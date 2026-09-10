"""Clarify that the Our Work summary is homepage-only copy."""

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doc("opero_site", "doctype", "our_work")
	rename_field("Our Work", "summary", "homepage_summary")
