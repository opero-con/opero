"""Drop the Opero prefix from public-site DocTypes.

The Opero Website workspace already provides that context, so
`Opero Site Home` becomes `Site Home`. `Site` stays to avoid Frappe's
Home workspace, Homepage, and Website Settings.
"""

from __future__ import annotations

import frappe

RENAMES = [
	("Opero Site Body Section", "Site Body Section"),
	("Opero Site Topic", "Site Topic"),
	("Opero Site Paragraph", "Site Paragraph"),
	("Opero Site Pillar", "Site Pillar"),
	("Opero Site Impact", "Site Impact"),
	("Opero Site Home Project", "Site Home Project"),
	("Opero Site Partner", "Site Partner"),
	("Opero Site Office", "Site Office"),
	("Opero Site Team Member", "Site Team Member"),
	("Opero Site Publication", "Site Publication"),
	("Opero Site Privacy", "Site Privacy"),
	("Opero Site Home", "Site Home"),
	("Opero Site Settings", "Site Settings"),
]


def execute():
	for old, new in RENAMES:
		if frappe.db.exists("DocType", old) and not frappe.db.exists("DocType", new):
			frappe.rename_doc("DocType", old, new, force=True, ignore_permissions=True)
		elif frappe.db.exists("DocType", old) and frappe.db.exists("DocType", new):
			frappe.delete_doc("DocType", old, force=True, ignore_permissions=True)
		_retarget_workspace_links(old, new)


def _retarget_workspace_links(old: str, new: str) -> None:
	# Workspace link_to is Data, so DocType rename does not update it.
	frappe.db.sql(
		"""
		UPDATE `tabWorkspace Link`
		SET link_to = %s
		WHERE link_to = %s AND link_type = 'DocType'
		""",
		(new, old),
	)
	frappe.db.sql(
		"""
		UPDATE `tabWorkspace Shortcut`
		SET link_to = %s
		WHERE link_to = %s AND `type` = 'DocType'
		""",
		(new, old),
	)
