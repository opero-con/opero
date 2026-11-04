"""Name capitalizations by their posting month, with stable document identifiers."""

import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils import getdate

SERIES = "ASC-.YY.MM.#"


def autoname(doc, _method=None):
	if not doc.posting_date:
		frappe.throw(_("Posting Date is required."), frappe.MandatoryError)

	posting_date = getdate(doc.posting_date)
	doc.name = make_autoname(f"ASC-{posting_date:%y%m}.#", doc=doc)
