"""Set the series shown for capitalizations without changing records or counters."""

import frappe

from opero.events.asset_capitalization import SERIES


def execute():
	for property_name in ("options", "default"):
		frappe.make_property_setter(
			{
				"doctype_or_field": "DocField",
				"doctype": "Asset Capitalization",
				"fieldname": "naming_series",
				"property": property_name,
				"value": SERIES,
				"property_type": "Text",
			},
			validate_fields_for_doctype=False,
		)
	frappe.clear_cache(doctype="Asset Capitalization")
