"""Rename WaSH* DocTypes to WASH* (Water And Sanitation Hygiene).

Existing Frappe Cloud sites still use the mixed-case WaSH DocType names.
"""

from __future__ import annotations

import frappe


RENAMES = [
	("WaSH Category", "WASH Category"),
	("WaSH Competency Category", "WASH Competency Category"),
	("WaSH Expert Profile", "WASH Expert Profile"),
	("WaSH Expertise Area", "WASH Expertise Area"),
	("WaSH Personnel", "WASH Personnel"),
]


def execute():
	for old, new in RENAMES:
		if frappe.db.exists("DocType", old) and not frappe.db.exists("DocType", new):
			frappe.rename_doc("DocType", old, new, force=True, ignore_permissions=True)
		elif frappe.db.exists("DocType", old) and frappe.db.exists("DocType", new):
			# Defensive: prefer the canonical WASH name if both somehow exist
			frappe.delete_doc("DocType", old, force=True, ignore_permissions=True)
