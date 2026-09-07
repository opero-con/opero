"""Retain native groups and newsletters, with confirmed-recipient eligibility."""

import frappe
from frappe import _
from frappe.email.doctype.email_group.email_group import EmailGroup
from frappe.email.doctype.email_group_member.email_group_member import EmailGroupMember
from frappe.email.doctype.newsletter.newsletter import Newsletter
from frappe.utils import validate_email_address

from opero.mailing.membership import MEMBER, email_key, ensure_member, require_manager


class MailingList(EmailGroup):
	def import_from(self, doctype):
		self.check_permission("write")
		require_manager()
		frappe.has_permission(doctype, "read", throw=True)
		meta = frappe.get_meta(doctype)
		field = next(
			(f.fieldname for f in meta.fields if f.options == "Email" and f.fieldtype == "Data"), None
		)
		if not field:
			frappe.throw(_("No Email field found in {0}").format(doctype))
		fields = [field] + (["unsubscribed"] if meta.has_field("unsubscribed") else [])
		for row in frappe.get_list(doctype, fields=fields, limit_page_length=0):
			if row.get(field) and validate_email_address(row[field], throw=False):
				ensure_member(self.name, row[field], row.get("unsubscribed", False))
		return self.update_total_subscribers()


class MailingListMember(EmailGroupMember):
	def autoname(self):
		if not self.email and self.get("custom_contact"):
			self.email = frappe.db.get_value("Contact", self.custom_contact, "email_id")
		self.name = readable_member_name(self.email_group, self.email)


class MailingNewsletter(Newsletter):
	def get_recipients(self):
		return sorted(
			set(
				frappe.get_all(
					MEMBER,
					filters={
						"email_group": ["in", self.get_email_groups()],
						"unsubscribed": 0,
						"custom_confirmation_status": "Confirmed",
					},
					pluck="email",
				)
			)
		)

	def send_newsletter(self, emails, test_email=False):
		# Recheck eligibility at queue time, including recipients cached by native validation.
		if not test_email:
			eligible = set(self.get_recipients())
			emails = sorted({email_key(e) for e in emails} & eligible)
			if not emails:
				return
		return super().send_newsletter(emails, test_email=test_email)


@frappe.whitelist(methods=["POST"])
def add_subscribers(name, email_list):
	require_manager()
	group = frappe.get_doc("Email Group", name)
	group.check_permission("write")
	if isinstance(email_list, str):
		email_list = email_list.replace(",", "\n").splitlines()
	for email in email_list:
		if email.strip():
			ensure_member(name, email)
		return group.update_total_subscribers()


def readable_member_name(group, email):
	email = email_key(email)
	if not email:
		return frappe.generate_hash(length=10)
	base = email
	if frappe.db.exists(MEMBER, base):
		base = f"{group}-{email}"

	if len(base) <= 140:
		return base

	suffix = frappe.generate_hash(f"{group}:{email}", 10)
	return f"{base[:129]}-{suffix}"
