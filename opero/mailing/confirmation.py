"""Explicit confirmation requests: fixed audience, recipient choice, one use."""

import hashlib
import secrets
from collections import defaultdict

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import escape_html, get_url, now_datetime

from opero.mailing.membership import (
	MEMBER,
	email_key,
	ensure_member,
	internal,
	record,
	require_manager,
	status,
)


def digest(token):
	return hashlib.sha256(str(token).encode()).hexdigest()


def candidates(contacts=None, mailing_lists=None):
	require_manager()
	contacts = frappe.parse_json(contacts) or []
	groups = frappe.parse_json(mailing_lists) or []
	filters = {}
	if contacts:
		emails = []
		for name in contacts:
			doc = frappe.get_doc("Contact", name)
			doc.check_permission("read")
			if doc.email_id:
				emails.append(email_key(doc.email_id))
		if not emails:
			return []
		filters["email"] = ["in", emails]
	if groups:
		filters["email_group"] = ["in", groups]
	if not contacts and not groups:
		frappe.throw(_("Select Contacts or a Mailing List first."))
	rows = frappe.get_list(
		MEMBER,
		filters=filters,
		fields=["name", "email", "email_group", "unsubscribed", "custom_confirmation_status"],
		limit_page_length=0,
		order_by="email, email_group",
	)
	return [
		dict(name=r.name, email=r.email, mailing_list=r.email_group, status=status(r))
		for r in rows
		if status(r) != "Confirmed"
	]


@frappe.whitelist()
def preview(contacts=None, mailing_lists=None, member=None):
	if member:
		require_manager()
		doc = frappe.get_doc(MEMBER, member)
		doc.check_permission("read")
		return (
			[]
			if status(doc) == "Confirmed"
			else [dict(name=doc.name, email=doc.email, mailing_list=doc.email_group, status=status(doc))]
		)
	return candidates(contacts, mailing_lists)


@frappe.whitelist(methods=["POST"])
def send_requests(members):
	require_manager()
	names = frappe.parse_json(members)
	if not isinstance(names, list) or not names or len(names) > 2000:
		frappe.throw(_("Select between 1 and 2,000 memberships from the recipient review."))
	by_email = defaultdict(list)
	for name in dict.fromkeys(names):
		doc = frappe.get_doc(MEMBER, name)
		doc.check_permission("write")
		if status(doc) != "Confirmed":
			by_email[doc.email].append(doc)
	for email, docs in by_email.items():
		create_request(email, docs)
	return {"emails": len(by_email)}


def create_request(email, members):
	"""Private primitive; callers must establish manager or public-signup authority."""
	from opero.mailing.membership import invalidate

	for member in members:
		invalidate(member.name)
	token = secrets.token_urlsafe(32)
	request = frappe.get_doc(
		{
			"doctype": "Mailing Confirmation Request",
			"email": email,
			"token_hash": digest(token),
			"status": "Pending",
			"sent_on": now_datetime(),
			"members": [{"member": m.name, "mailing_list": m.email_group} for m in members],
		}
	).insert(ignore_permissions=True)
	url = get_url("/mailing-confirmation?token=" + token)
	lists = "".join(f"<li>{escape_html(m.email_group)}</li>" for m in members)
	frappe.sendmail(
		recipients=[email],
		subject=_("Confirm your Mailing Lists"),
		message=f"<p>{_('Please choose which Mailing Lists you want to receive emails from:')}</p>"
		f"<ul>{lists}</ul><p><a href='{escape_html(url)}'>{_('Review and confirm')}</a></p>"
		f"<p>{_('If you did not request this, you can ignore this email.')}</p>",
		reference_doctype=request.doctype,
		reference_name=request.name,
	)
	return request


def get_request(token, lock=False):
	if not token or len(str(token)) > 128:
		frappe.throw(_("This confirmation link is invalid or has already been used."))
	rows = frappe.db.sql(
		"""select name from `tabMailing Confirmation Request`
		where token_hash=%s and status='Pending'"""
		+ (" for update" if lock else ""),
		(digest(token),),
	)
	if not rows:
		frappe.throw(_("This confirmation link is invalid or has already been used."))
	doc = frappe.get_doc("Mailing Confirmation Request", rows[0][0])
	for row in doc.members:
		member = frappe.db.get_value(MEMBER, row.member, ["email", "email_group"], as_dict=True)
		if not member or member.email != doc.email or member.email_group != row.mailing_list:
			frappe.throw(_("This request no longer matches your memberships. Please request a new link."))
	return doc


def confirm(token, groups):
	request = get_request(token, lock=True)
	groups = frappe.parse_json(groups)
	if (
		not isinstance(groups, list)
		or not groups
		or not set(groups) <= {m.mailing_list for m in request.members}
	):
		frappe.throw(_("Choose at least one of the Mailing Lists in this request."))
	# Consume first: status hooks invalidate other requests, not this completed one.
	request.db_set({"status": "Used", "completed_on": now_datetime()})
	for row in request.members:
		if row.mailing_list in groups:
			with internal():
				member = frappe.get_doc(MEMBER, row.member)
				member.unsubscribed = 0
				member.custom_confirmation_status = "Confirmed"
				member.save(ignore_permissions=True)
			record(member, "Recipient confirmed")
	return len(set(groups))


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=3600)
def subscribe(email, email_group=None):
	"""Preserve Frappe's public signup endpoint, using tracked confirmation requests."""
	from frappe.email.doctype.newsletter.newsletter import get_default_email_group

	group = email_group or get_default_email_group()
	if not frappe.db.exists("Email Group", group):
		frappe.throw(_("Mailing List not found."))
	member = ensure_member(group, email)
	if status(member) != "Confirmed":
		create_request(member.email, [member])
	return {"message": _("If confirmation is needed, an email will be sent.")}


@frappe.whitelist(allow_guest=True)
def legacy_confirmation(email=None, email_group=None):
	# Legacy links lack request state and cannot safely distinguish rejoining from replay.
	frappe.respond_as_web_page(
		_("Request a new confirmation"),
		_("Please request a new confirmation email. Existing subscriptions are unchanged."),
	)
