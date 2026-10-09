"""Keep publication-only Desk accounts out of mailing data granted to All."""

import frappe


def is_publication_only_user(user=None):
	roles = set(frappe.get_roles(user or frappe.session.user))
	return "Website Publication Publisher" in roles and not roles.difference(
		{"Website Publication Publisher", "All", "Guest", "Desk User"}
	)


def mailing_permission_query(user=None):
	return "1=0" if is_publication_only_user(user) else None


def mailing_has_permission(doc, ptype=None, user=None):
	return False if is_publication_only_user(user) else None
