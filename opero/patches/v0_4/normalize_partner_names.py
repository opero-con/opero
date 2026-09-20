from __future__ import annotations

import re

import frappe

from opero.opero_site.doctype.partner.partner import make_partner_name


PARTNER_ID_PATTERN = re.compile(r"^P\d{5}$")


def execute():
	if not frappe.db.exists("DocType", "Partner"):
		return

	for old_name in frappe.get_all("Partner", pluck="name"):
		if PARTNER_ID_PATTERN.fullmatch(old_name):
			continue
		frappe.rename_doc("Partner", old_name, make_partner_name(), force=True)
