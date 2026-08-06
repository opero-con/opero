"""Grant and revoke a user's access to an entity.

Cross-entity work is normal at Opero — someone employed by one entity is
regularly booked onto another entity's project. Access is granted with Company
User Permissions, which Frappe then applies to every document carrying a company
field, including all of Opero's project-scoped DocTypes.

The rule Frappe applies is easy to get wrong by hand:

* a user with **no** Company User Permission sees **every** entity;
* a user with **one or more** sees **only** those.

So granting one person access to a second entity means making sure they also
still hold a permission for their own — otherwise "adding" access silently
removes it everywhere else. That is what this module exists to get right.
"""

from __future__ import annotations

import frappe
from frappe import _

ALLOWED_ROLE = "System Manager"


def _check_manage_permission() -> None:
	if ALLOWED_ROLE not in frappe.get_roles():
		frappe.throw(_("Not permitted to manage entity access."), frappe.PermissionError)


def get_entities() -> list[dict]:
	"""Every company on the site, with the short name people recognise.

	This page renders its own markup, so it does not pass through the link
	formatter that substitutes the display name elsewhere; it falls back to the
	registered name the same way.
	"""
	entities = frappe.get_all(
		"Company",
		fields=["name", "abbr", "default_currency", "custom_display_name"],
		order_by="name",
	)
	for entity in entities:
		entity["label"] = entity.get("custom_display_name") or entity["name"]
	return entities


@frappe.whitelist()
def get_access_matrix() -> dict:
	"""Users, entities, and who may currently see what."""
	_check_manage_permission()

	entities = get_entities()
	users = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		fields=["name", "full_name"],
		order_by="full_name",
	)

	granted: dict[str, list[str]] = {}
	for row in frappe.get_all(
		"User Permission",
		filters={"allow": "Company"},
		fields=["user", "for_value"],
		limit_page_length=0,
	):
		granted.setdefault(row.user, []).append(row.for_value)

	employer = {
		row.user_id: row.company
		for row in frappe.get_all(
			"Employee",
			filters={"user_id": ("is", "set")},
			fields=["user_id", "company"],
			limit_page_length=0,
		)
		if row.user_id
	}

	return {
		"entities": entities,
		"users": [
			{
				"user": user.name,
				"full_name": user.full_name or user.name,
				"employer": employer.get(user.name),
				# An empty list means "unrestricted": Frappe shows this user everything.
				"allowed": sorted(granted.get(user.name, [])),
			}
			for user in users
		],
	}


@frappe.whitelist()
def set_access(user: str, companies: str | list[str]) -> dict:
	"""Make `user`'s Company User Permissions exactly `companies`.

	An empty list clears every Company permission, which restores unrestricted
	access to all entities — the Frappe default.
	"""
	_check_manage_permission()

	if isinstance(companies, str):
		companies = frappe.parse_json(companies)
	wanted = {c for c in (companies or []) if c}

	unknown = wanted - {entity["name"] for entity in get_entities()}
	if unknown:
		frappe.throw(_("Unknown company: {0}").format(", ".join(sorted(unknown))))

	if not frappe.db.exists("User", user):
		frappe.throw(_("Unknown user: {0}").format(user))

	# Read, diff and write are one unit. Two administrators saving this user at
	# once would otherwise each diff against the same starting set and produce a
	# union of both selections, granting an entity neither of them ticked.
	frappe.db.sql("SELECT name FROM `tabUser` WHERE name = %s FOR UPDATE", user)

	existing = {
		row.for_value: row.name
		for row in frappe.get_all(
			"User Permission",
			filters={"user": user, "allow": "Company"},
			fields=["name", "for_value"],
		)
	}

	for company in sorted(wanted - set(existing)):
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": "Company",
				"for_value": company,
				# Applies the restriction to every DocType with a Company link,
				# which is the whole point of stamping company onto child documents.
				"apply_to_all_doctypes": 1,
			}
		).insert(ignore_permissions=True)

	for company in set(existing) - wanted:
		frappe.delete_doc("User Permission", existing[company], ignore_permissions=True)

	frappe.db.commit()
	frappe.clear_cache(user=user)

	return {"user": user, "allowed": sorted(wanted)}
