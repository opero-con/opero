"""Allow Material Request items grid edits after submit.

Budget Line already has allow_on_submit on the child field, but Frappe only
enables inline table editing when the parent Table field (`items`) is also
allow_on_submit. Without that, the grid stays Read and only the row dialog
exposes allow-on-submit fields.

`import_fc_site_config` only upserts once, so flipping the property setter in
`data/fc_site_config/property_setter.json` does not reach sites where that
patch already ran. This does.
"""

from __future__ import annotations

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

SETTER_NAME = "Material Request-items-allow_on_submit"


def execute():
	if not frappe.db.exists("DocType", "Material Request"):
		return
	if not frappe.get_meta("Material Request").has_field("items"):
		return

	if frappe.db.exists("Property Setter", SETTER_NAME):
		frappe.db.set_value("Property Setter", SETTER_NAME, "value", "1")
	else:
		make_property_setter(
			"Material Request",
			"items",
			"allow_on_submit",
			"1",
			"Check",
			validate_fields_for_doctype=False,
		)

	frappe.clear_cache(doctype="Material Request")
