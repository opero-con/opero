"""Rename mailing list members to their subscription email addresses."""

import frappe

from opero.mailing.membership import MEMBER, email_key


def execute():
	rows = frappe.get_all(MEMBER, fields=["name", "email"], order_by="creation")
	targets = {}

	for row in rows:
		target = email_key(row.email)
		if target:
			targets.setdefault(target, []).append(row.name)

	duplicates = {email: names for email, names in targets.items() if len(names) > 1}
	if duplicates:
		details = "; ".join(f"{email}: {', '.join(names)}" for email, names in duplicates.items())
		frappe.throw(
			"Cannot normalize Mailing List Member names because duplicate email addresses exist: "
			+ details
		)

	for row in rows:
		target = email_key(row.email)
		if target and row.name != target:
			frappe.rename_doc(MEMBER, row.name, target, force=True)
