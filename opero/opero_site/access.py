"""Keep publication editors out of incidental mailing permissions granted to All."""

import frappe


def is_publication_editor(user=None):
	user = user or frappe.session.user
	return frappe.has_permission("Publication", "write", user=user) and not frappe.has_permission(
		"Site Settings", "write", user=user
	)


def has_explicit_permission(doctype, ptype="read", user=None):
	"""Respect Role Permission Manager grants without treating All as staff access."""
	roles = set(frappe.get_roles(user or frappe.session.user)) - {"All", "Guest", "Desk User"}
	return any(
		row.role in roles and row.permlevel == 0 and row.get(ptype)
		for row in frappe.get_meta(doctype).permissions
	)


def mailing_permission_query(user=None, doctype="Email Group"):
	return "1=0" if is_publication_editor(user) and not has_explicit_permission(doctype, user=user) else None


def mailing_member_permission_query(user=None):
	return mailing_permission_query(user, "Email Group Member")


def newsletter_permission_query(user=None):
	return mailing_permission_query(user, "Newsletter")


def mailing_has_permission(doc, ptype=None, user=None):
	if is_publication_editor(user) and not has_explicit_permission(doc.doctype, ptype or "read", user):
		return False
	return None
