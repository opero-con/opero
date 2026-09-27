"""Show Rate in the Material Request items grid and reset saved grid columns.

`import_fc_site_config` only upserts once, so the new property setter in
`data/fc_site_config/property_setter.json` does not reach sites where it has
already run. Saved per-user GridView columns override the default, so drop them
for this table so everyone sees Item Code, Budget Line, Quantity, UOM and Rate.
"""

import json

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.model.utils.user_settings import sync_user_settings

PARENT = "Material Request"
CHILD = "Material Request Item"


def execute():
	if not frappe.db.exists("DocType", CHILD):
		return

	name = f"{CHILD}-rate-in_list_view"
	if frappe.db.exists("Property Setter", name):
		frappe.db.set_value("Property Setter", name, "value", "1")
	else:
		make_property_setter(CHILD, "rate", "in_list_view", "1", "Check", validate_fields_for_doctype=False)

	reset_saved_grid_columns()
	frappe.clear_cache(doctype=CHILD)


def reset_saved_grid_columns():
	sync_user_settings()
	rows = frappe.db.sql(
		"select `user`, `data` from `__UserSettings` where `doctype`=%s", PARENT, as_dict=True
	)
	for row in rows:
		data = json.loads(row.data or "{}")
		if data.get("GridView", {}).pop(CHILD, None) is None:
			continue
		frappe.db.sql(
			"update `__UserSettings` set `data`=%s where `user`=%s and `doctype`=%s",
			(json.dumps(data), row.user, PARENT),
		)
	frappe.cache.delete_value("_user_settings")
