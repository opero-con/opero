"""Public signup without a separate confirmation step.

Recipients opt out with the unsubscribe link on every newsletter.
"""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint

from opero.mailing.membership import ensure_member, internal, status


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=3600)
def subscribe(email, email_group=None):
	"""Preserve Frappe's public signup endpoint; members are active immediately."""
	from frappe.email.doctype.newsletter.newsletter import get_default_email_group

	group = email_group or get_default_email_group()
	if not frappe.db.exists("Email Group", group):
		frappe.throw(_("Mailing List not found."))
	member = ensure_member(group, email)
	if cint(member.unsubscribed) or status(member) != "Confirmed":
		with internal():
			member.unsubscribed = 0
			member.custom_confirmation_status = "Confirmed"
			member.save(ignore_permissions=True)
	return {"message": _("You have been subscribed to this mailing list.")}


@frappe.whitelist(allow_guest=True)
def legacy_confirmation(email=None, email_group=None):
	# Old Frappe confirmation links are unused; memberships no longer need them.
	frappe.respond_as_web_page(
		_("No confirmation needed"),
		_(
			"Mailing list memberships are active without a confirmation email. "
			"Use the unsubscribe link in any newsletter to stop receiving emails."
		),
	)
