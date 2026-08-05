"""Stop hiding the company field on Timesheet and Travel Request.

Both were hidden when the site ran a single company and the field was noise.
With more than one entity they are the two forms where cross-entity work
actually shows up — someone employed by one entity logging time or travel
against another entity's project — so the field that decides which entity bears
the cost has to be on screen.

The form still does not let anyone type into it: `entity_scope.js` locks it as
soon as a project is chosen, and the server re-derives it on every save.

`import_fc_site_config` only upserts, so flipping the value in
`data/fc_site_config/property_setter.json` does not reach sites where it has
already run. This does.
"""

from __future__ import annotations

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

DOCTYPES = ("Timesheet", "Travel Request")


def execute():
	for doctype in DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		if not frappe.get_meta(doctype).has_field("company"):
			continue

		name = f"{doctype}-company-hidden"
		if frappe.db.exists("Property Setter", name):
			frappe.db.set_value("Property Setter", name, "value", "0")
		else:
			make_property_setter(
				doctype,
				"company",
				"hidden",
				"0",
				"Check",
				validate_fields_for_doctype=False,
			)

	frappe.clear_cache()
