"""Material Request event handlers."""

from __future__ import annotations

from frappe.utils import flt


def validate_material_request(doc, _method=None):
	doc.custom_total = flt(
		sum(flt(item.qty) * flt(item.rate) for item in doc.items), doc.precision("custom_total")
	)
