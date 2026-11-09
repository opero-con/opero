"""Name tax rules by transaction type and validity start month."""

import frappe
from frappe import _
from frappe.model.naming import getseries
from frappe.utils import getdate


def autoname(doc, _method=None):
	initial = {"Sales": "S", "Purchase": "P"}.get(doc.tax_type)
	if not initial:
		frappe.throw(_("Select Sales or Purchase as the Tax Type."), frappe.ValidationError)

	period = getdate(doc.from_date).strftime("%m%y") if doc.from_date else "UNDATED"
	prefix = f"TRL-{initial}-{period}"
	while True:
		sequence = int(getseries(prefix, 2))
		name = prefix if sequence == 1 else f"{prefix}-{sequence:02d}"
		if not frappe.db.exists("Tax Rule", name):
			doc.name = name
			return
