"""Lay out the Material Request header in two aligned rows.

Row one: Purpose, Transaction Date, Required By. Row two: Company, Price List,
Set Target Warehouse.

`import_fc_site_config` only upserts once, so the new layout fields and field
order in `data/fc_site_config` do not reach sites where it has already run.
"""

import json

import frappe

from opero.patches.v0_2.import_fc_site_config import DATA_DIR, _upsert

DOCUMENTS = {
	"custom_field.json": [
		"Material Request-custom_required_by_column",
		"Material Request-custom_request_details_section",
		"Material Request-custom_request_details_column",
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
