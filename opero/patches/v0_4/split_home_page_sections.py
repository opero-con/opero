"""Split Home Page into focused Hero/About/Pillars/Impacts/Projects/Partners singles."""

from __future__ import annotations

import frappe
from frappe.utils import cstr

SECTION_DOCTYPES = ("home_hero", "home_about", "home_pillars", "home_impacts", "home_projects", "home_partners")
SCALAR_FIELDS = {
	"Home Hero": ("hero_eyebrow", "hero_title", "hero_description"),
	"Home About": ("about_title", "about_body"),
}
CHILD_TABLES = {
	"Hero Image": ("hero_images", "Home Hero"),
	"Pillar": ("pillars", "Home Pillars"),
	"Impact": ("impacts", "Home Impacts"),
	"Home Project": ("projects", "Home Projects"),
	"Partner": ("partners", "Home Partners"),
}


def execute():
	if not frappe.db.exists("DocType", "Home Page"):
		return

	# Read legacy Home Page Singles values before reload_doc drops them from its meta.
	scalars = {
		target: {field: _legacy_home_page_single(field) for field in fields}
		for target, fields in SCALAR_FIELDS.items()
	}

	for doctype in SECTION_DOCTYPES:
		frappe.reload_doc("opero_site", "doctype", doctype)
	frappe.reload_doc("opero_site", "doctype", "home_page")

	for target, values in scalars.items():
		for field, value in values.items():
			if value:
				frappe.db.set_single_value(target, field, value, update_modified=False)

	for child_doctype, (parentfield, target) in CHILD_TABLES.items():
		if not frappe.db.table_exists(child_doctype):
			continue
		frappe.db.sql(
			f"""
			UPDATE `tab{child_doctype}`
			SET parent = %s, parenttype = %s
			WHERE parent = 'Home Page' AND parenttype = 'Home Page' AND parentfield = %s
			""",
			(target, target, parentfield),
		)

	frappe.db.sql("DELETE FROM `tabSingles` WHERE doctype = 'Home Page' AND field != 'status'")


def _legacy_home_page_single(field: str) -> str:
	value = frappe.db.sql(
		"SELECT value FROM tabSingles WHERE doctype = 'Home Page' AND field = %s",
		(field,),
	)
	return cstr(value[0][0] if value else "").strip()
