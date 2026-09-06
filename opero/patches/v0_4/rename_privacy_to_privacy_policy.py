"""Rename Privacy to Privacy policy so Cubenet matches the public page title."""

from __future__ import annotations

import frappe

OLD = "Privacy"
NEW = "Privacy policy"


def execute():
	if frappe.db.exists("DocType", OLD) and not frappe.db.exists("DocType", NEW):
		frappe.rename_doc("DocType", OLD, NEW, force=True)
	elif frappe.db.exists("DocType", OLD) and frappe.db.exists("DocType", NEW):
		frappe.delete_doc("DocType", OLD, force=True, ignore_permissions=True)

	# Singles store the DocType name in `doctype`; rename_doc may leave it stale.
	frappe.db.sql(
		"""
		UPDATE `tabSingles`
		SET doctype = %s
		WHERE doctype = %s
		""",
		(NEW, OLD),
	)
	# Single document name mirrors the DocType name.
	frappe.db.sql(
		"""
		UPDATE `tabSingles`
		SET value = %s
		WHERE doctype = %s AND field = 'name' AND value = %s
		""",
		(NEW, NEW, OLD),
	)
	frappe.reload_doc("opero_site", "doctype", "privacy_policy", force=True)
	_retarget_workspace_links(OLD, NEW)
	frappe.reload_doc("opero_site", "workspace", "opero_website", force=True)


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
		SET link_to = %s, label = %s
		WHERE link_to = %s AND `type` = 'DocType'
		""",
		(new, new, old),
	)
	frappe.db.sql(
		"""
		UPDATE `tabWorkspace Link`
		SET label = %s
		WHERE link_to = %s AND link_type = 'DocType' AND label = %s
		""",
		(new, new, old),
	)
