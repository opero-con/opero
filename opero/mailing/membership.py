"""Contact membership is a projection of Frappe's email-based subscriptions.

No save/import sends mail. Internal updates use a server-only context, never a
client-supplied document flag. Membership history survives member deletion.
Members are eligible until they unsubscribe via the newsletter footer link.
"""

from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import cint, validate_email_address

MEMBER = "Email Group Member"
CHILD = "Contact Mailing List"
FIELD = "custom_mailing_lists"


@contextmanager
def internal():
	previous = frappe.flags.opero_mailing_internal
	frappe.flags.opero_mailing_internal = True
	try:
		yield
	finally:
		frappe.flags.opero_mailing_internal = previous


def email_key(email):
	return (email or "").strip().lower()


def manager():
	return frappe.session.user == "Administrator" or "Newsletter Manager" in frappe.get_roles()


def require_manager():
	if not manager():
		frappe.throw(
			_("Only Newsletter Managers can send or reactivate subscriptions."), frappe.PermissionError
		)


@frappe.whitelist()
def contact_primary_email(contact):
	doc = frappe.get_doc("Contact", contact)
	doc.check_permission("read")
	if not doc.email_id:
		frappe.throw(_("Set a primary email on the selected Contact before adding this member."))
	return email_key(doc.email_id)


def status(member):
	if cint(member.unsubscribed):
		return "Unsubscribed"
	return "Confirmed"


def record(member, action, contact=None):
	frappe.get_doc(
		{
			"doctype": "Mailing Membership Event",
			"email": member.email,
			"mailing_list": member.email_group,
			"member": member.name,
			"contact": contact,
			"action": action,
			"subscription_status": status(member),
			"actor": frappe.session.user,
		}
	).insert(ignore_permissions=True)


def member_validate(doc, method=None):
	old = doc.get_doc_before_save()
	contact = doc.get("custom_contact")
	if contact:
		if not frappe.flags.opero_mailing_internal and (not old or old.get("custom_contact") != contact):
			frappe.get_doc("Contact", contact).check_permission("read")
		primary_email = frappe.db.get_value("Contact", contact, "email_id")
		if not primary_email:
			frappe.throw(_("Set a primary email on the selected Contact before adding this member."))
		doc.email = primary_email
	doc.email = email_key(doc.email)
	validate_email_address(doc.email, throw=True)
	if not old or frappe.flags.opero_mailing_internal:
		return
	if cint(old.unsubscribed) and not cint(doc.unsubscribed):
		require_manager()


def member_updated(doc, method=None):
	old = doc.get_doc_before_save()
	if old and (old.email != doc.email or old.email_group != doc.email_group):
		record(old, "Moved")
		sync_email(old.email)
	if not old:
		record(doc, "Added")
	elif status(old) != status(doc):
		record(doc, "Status changed")
	if not frappe.flags.opero_mailing_sync:
		sync_email(doc.email)


def member_removed(doc, method=None):
	record(doc, "Removed")


def member_after_delete(doc, method=None):
	if not frappe.flags.opero_mailing_sync:
		sync_email(doc.email)


def prepare_list_merge(source, target):
	"""Drop overlapping source members and child links before a list merge rename.

	Frappe rewrites every Link to the source list onto the target. Email Group
	Member uniqueness is (email_group, email), so shared addresses must leave
	the source first. Contact and Newsletter child rows that already point at
	the target are removed so the rewrite cannot duplicate them.
	"""
	source_members = frappe.get_all(
		MEMBER,
		filters={"email_group": source},
		fields=["name", "email", "unsubscribed", "custom_contact"],
	)
	for sm in source_members:
		target_name = frappe.db.get_value(
			MEMBER, {"email_group": target, "email": email_key(sm.email)}
		)
		if not target_name:
			continue
		_fold_member_into(target_name, sm)
		frappe.delete_doc(MEMBER, sm.name, ignore_permissions=True)

	_drop_duplicate_links(CHILD, "mailing_list", source, target)
	_drop_duplicate_links("Newsletter Email Group", "email_group", source, target)


def _fold_member_into(target_name, source_member):
	"""Keep the surviving target row; prefer unsubscribe and Contact link."""
	target = frappe.get_doc(MEMBER, target_name)
	changed = False
	if cint(source_member.unsubscribed) and not cint(target.unsubscribed):
		target.unsubscribed = 1
		changed = True
	if not target.get("custom_contact") and source_member.get("custom_contact"):
		target.custom_contact = source_member.custom_contact
		changed = True
	if changed:
		with internal():
			target.save(ignore_permissions=True)


def _drop_duplicate_links(doctype, fieldname, source, target):
	if not frappe.db.exists("DocType", doctype):
		return
	keep = set(frappe.get_all(doctype, filters={fieldname: target}, pluck="parent"))
	if not keep:
		return
	for name in frappe.get_all(
		doctype, filters={fieldname: source, "parent": ["in", list(keep)]}, pluck="name"
	):
		frappe.db.delete(doctype, {"name": name})


def sync_email(email, exclude=None):
	"""Refresh Contact selections and statuses, including shared email Contacts.

	Direct child writes avoid re-running unrelated Contact integration hooks.
	Touch modified so stale Contact forms cannot silently overwrite membership.
	"""
	if not email:
		return
	# A Contact may move while others keep using the old subscription address.
	# Drop navigation links that no longer match that address.
	if frappe.get_meta(MEMBER).has_field("custom_contact"):
		for member in frappe.get_all(
			MEMBER,
			filters={"email": email_key(email), "custom_contact": ["is", "set"]},
			fields=["name", "custom_contact"],
		):
			if email_key(frappe.db.get_value("Contact", member.custom_contact, "email_id")) != email_key(
				email
			):
				frappe.db.set_value(MEMBER, member.name, "custom_contact", None)
	members = frappe.get_all(
		MEMBER,
		filters={"email": email_key(email)},
		fields=["email_group", "unsubscribed"],
		order_by="email_group",
	)
	for contact in frappe.get_all("Contact", filters={"email_id": email_key(email)}, pluck="name"):
		if contact == exclude:
			continue
		rows = frappe.get_all(
			CHILD,
			filters={"parent": contact, "parenttype": "Contact", "parentfield": FIELD},
			fields=["mailing_list", "subscription_status"],
			order_by="idx",
		)
		wanted = [(m.email_group, status(m)) for m in members]
		if [(r.mailing_list, r.subscription_status) for r in rows] == wanted:
			continue
		frappe.db.delete(CHILD, {"parent": contact, "parenttype": "Contact", "parentfield": FIELD})
		for idx, (group, state) in enumerate(wanted, 1):
			frappe.get_doc(
				{
					"doctype": CHILD,
					"parent": contact,
					"parenttype": "Contact",
					"parentfield": FIELD,
					"idx": idx,
					"mailing_list": group,
					"subscription_status": state,
				}
			).db_insert()
		frappe.db.set_value("Contact", contact, "modified", frappe.utils.now(), update_modified=False)
		frappe.clear_document_cache("Contact", contact)


def ensure_member(group, email, unsubscribed=False):
	name = frappe.db.get_value(MEMBER, {"email_group": group, "email": email_key(email)})
	if name:
		doc = frappe.get_doc(MEMBER, name)
		# Never erase an unsubscribe while synchronizing a new Contact/address.
		if unsubscribed and not doc.unsubscribed:
			with internal():
				doc.unsubscribed = 1
				doc.save(ignore_permissions=True)
		return doc
	with internal():
		return frappe.get_doc(
			{
				"doctype": MEMBER,
				"email_group": group,
				"email": email_key(email),
				"unsubscribed": int(unsubscribed),
			}
		).insert(ignore_permissions=True)


def remove_member(group, email):
	name = frappe.db.get_value(MEMBER, {"email_group": group, "email": email_key(email)})
	if name:
		frappe.delete_doc(MEMBER, name, ignore_permissions=True)


def contact_validate(doc, method=None):
	groups = [r.mailing_list for r in doc.get(FIELD, [])]
	if len(groups) != len(set(groups)):
		frappe.throw(_("A Contact can belong to each Mailing List only once."))
	old = doc.get_doc_before_save()
	old_states = {r.mailing_list: r.subscription_status for r in old.get(FIELD, [])} if old else {}
	# Ignore statuses supplied through imports/API; the server owns them.
	for row in doc.get(FIELD, []):
		row.subscription_status = old_states.get(row.mailing_list, "No email")


def contact_updated(doc, method=None):
	if frappe.flags.opero_mailing_internal:
		return
	old = doc.get_doc_before_save()
	previous = {r.mailing_list: r.subscription_status for r in old.get(FIELD, [])} if old else {}
	groups = {r.mailing_list for r in doc.get(FIELD, [])}
	email = email_key(doc.email_id)
	old_email = email_key(old.email_id) if old else ""
	linked_groups = set()
	previous_sync = frappe.flags.opero_mailing_sync
	frappe.flags.opero_mailing_sync = True
	try:
		if old_email and old_email != email:
			# Moving one Contact must not remove delivery for other Contacts still at the old address.
			others = frappe.db.exists("Contact", {"email_id": old_email, "name": ["!=", doc.name]})
			for group in previous:
				member = frappe.db.get_value(
					MEMBER,
					{"email": old_email, "email_group": group},
					["name", "unsubscribed", "custom_contact"],
					as_dict=True,
				)
				if member:
					if member.custom_contact == doc.name:
						linked_groups.add(group)
					previous[group] = status(member)
					if not others:
						remove_member(group, old_email)
		if email:
			if email == old_email:
				for group in previous.keys() - groups:
					remove_member(group, email)
			for group in sorted(groups):
				member = ensure_member(
					group, email, previous.get(group) == "Unsubscribed" and email != old_email
				)
				if group in linked_groups and not member.get("custom_contact"):
					member.db_set("custom_contact", doc.name)
		else:
			for row in doc.get(FIELD, []):
				row.db_set(
					"subscription_status",
					"Unsubscribed" if previous.get(row.mailing_list) == "Unsubscribed" else "No email",
				)
	finally:
		frappe.flags.opero_mailing_sync = previous_sync
	if old_email and old_email != email:
		sync_email(old_email)
	if email:
		sync_email(email)
	# Return the persisted projection, not the submitted stale child collection.
	doc.set(
		FIELD,
		frappe.get_all(
			CHILD,
			filters={"parent": doc.name, "parenttype": "Contact", "parentfield": FIELD},
			fields=["*"],
			order_by="idx",
		),
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def search_lists(doctype, txt, searchfield, start, page_len, filters):
	frappe.has_permission("Contact", "read", throw=True)
	return frappe.get_all(
		"Email Group",
		filters={"name": ["like", f"%{txt}%"]},
		fields=["name"],
		limit_start=start,
		limit_page_length=page_len,
		as_list=True,
	)


@frappe.whitelist()
def contact_status(contact):
	doc = frappe.get_doc("Contact", contact)
	doc.check_permission("read")
	return [
		{"mailing_list": r.mailing_list, "status": r.subscription_status, "email": doc.email_id or ""}
		for r in doc.get(FIELD, [])
	]


@frappe.whitelist(methods=["POST"])
def bulk_membership(contacts, mailing_lists, action="add"):
	contacts, groups = frappe.parse_json(contacts), frappe.parse_json(mailing_lists)
	if not isinstance(contacts, list) or not isinstance(groups, list) or action not in ("add", "remove"):
		frappe.throw(_("Select Contacts, Mailing Lists, and a valid action."))
	if len(contacts) > 500:
		frappe.throw(_("Select up to 500 Contacts per operation."))
	for name in dict.fromkeys(contacts):
		doc = frappe.get_doc("Contact", name)
		doc.check_permission("write")
		existing = {r.mailing_list for r in doc.get(FIELD, [])}
		if action == "add":
			for group in set(groups) - existing:
				doc.append(FIELD, {"mailing_list": group})
		else:
			doc.set(FIELD, [r for r in doc.get(FIELD, []) if r.mailing_list not in groups])
		doc.save()
	return {"contacts": len(set(contacts)), "message": _("Memberships saved. No emails were sent.")}
