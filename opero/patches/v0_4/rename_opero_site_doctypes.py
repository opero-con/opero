"""Drop the Opero Site prefix from public-site DocTypes.

The Opero Website workspace already provides that context.
Home stays Home Page so it does not collide with Desk Home or ERPNext Homepage.
Home Project stays distinct from ERPNext Project.
"""

from __future__ import annotations

import frappe


RENAMES = [
	("Opero Site Body Section", "Body Section"),
	("Opero Site Topic", "Topic"),
	("Opero Site Paragraph", "Paragraph"),
	("Opero Site Pillar", "Pillar"),
	("Opero Site Impact", "Impact"),
	("Opero Site Home Project", "Home Project"),
	("Opero Site Partner", "Partner"),
	("Opero Site Office", "Office"),
	("Opero Site Publish Log", "Publish Log"),
	("Opero Site Team Member", "Team Member"),
	("Opero Site Publication", "Publication"),
	("Opero Site Privacy", "Privacy"),
	("Opero Site Home", "Home Page"),
	("Opero Site Settings", "Site Settings"),
	("Opero Site Publisher", "Publisher"),
]


def execute():
	for old, new in RENAMES:
		if frappe.db.exists("DocType", old) and not frappe.db.exists("DocType", new):
			frappe.rename_doc("DocType", old, new, force=True)
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
