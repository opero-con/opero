"""Add a right-aligned Total below the Material Request items and backfill existing requests.

`import_fc_site_config` only upserts once, so the new field and field order in
`data/fc_site_config` do not reach sites where it has already run.
"""

import json

import frappe
from frappe.model.meta import get_field_precision

from opero.patches.v0_2.import_fc_site_config import DATA_DIR, _upsert

DOCUMENTS = {
	"custom_field.json": [
		"Material Request-custom_total_section",
		"Material Request-custom_total_left_column",
		"Material Request-custom_total_right_column",
		"Material Request-custom_total",
	],
	"property_setter.json": ["Material Request-main-field_order"],
}


def execute():
	if not frappe.db.exists("DocType", "Material Request"):
		return

	for filename, names in DOCUMENTS.items():
		docs = {doc["name"]: doc for doc in json.loads((DATA_DIR / filename).read_text())}
		for name in names:
			_upsert(docs[name])
	frappe.clear_cache(doctype="Material Request")

	precision = get_field_precision(frappe.get_meta("Material Request").get_field("custom_total"))
	frappe.db.sql(
		"""
		update `tabMaterial Request` request
		set custom_total = (
			select round(coalesce(sum(item.qty * item.rate), 0), %s)
			from `tabMaterial Request Item` item
			where item.parent = request.name and item.parenttype = 'Material Request'
		)
		""",
		precision,
	)
