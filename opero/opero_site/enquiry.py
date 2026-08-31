from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cstr, escape_html, validate_email_address

SOURCE_WEBSITE = "Website"
MAX_NAME = 100
MAX_EMAIL = 254
MAX_ORG = 160
MAX_SUBJECT = 120
MAX_MESSAGE = 5000


@frappe.whitelist(methods=["POST"])
def create_website_enquiry(
	full_name: str,
	email: str,
	subject: str,
	message: str,
	organization: str | None = None,
	consent: str | None = None,
) -> dict:
	if frappe.session.user == "Guest":
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	sender_name = _clean(full_name, MAX_NAME)
	sender = _clean(email, MAX_EMAIL).lower()
	org = _clean(organization, MAX_ORG)
	enquiry_subject = _clean(subject, MAX_SUBJECT)
	body = _clean(message, MAX_MESSAGE)
	agreed = cstr(consent).strip().lower() in ("yes", "true", "1")

	if not sender_name or not enquiry_subject or not body or not agreed:
		frappe.throw(_("Please complete all required fields with valid information."))
	validate_email_address(sender, throw=True)

	html, text = _enquiry_body(sender_name, sender, org, enquiry_subject, body)
	doc = frappe.get_doc(
		{
			"doctype": "Communication",
			"subject": enquiry_subject,
			"communication_medium": "Other",
			"sender": sender,
			"sender_full_name": sender_name,
			"content": html,
			"text_content": text,
			"communication_type": "Communication",
			"status": "Open",
			"sent_or_received": "Received",
			"custom_source": SOURCE_WEBSITE,
		}
	)
	doc.insert(ignore_permissions=True)
	_notify(doc, sender)
	return {"name": doc.name}


def _clean(value, limit: int) -> str:
	return cstr(value).replace("\x00", "").strip()[:limit]


def _enquiry_body(
	sender_name: str, sender: str, org: str, subject: str, message: str
) -> tuple[str, str]:
	org_display = org or "Not provided"
	text = "\n".join(
		[
			f"Name: {sender_name}",
			f"Email: {sender}",
			f"Organization: {org_display}",
			f"Subject: {subject}",
			"",
			message,
		]
	)
	html = (
		f"<p><strong>Name:</strong> {escape_html(sender_name)}</p>"
		f"<p><strong>Email:</strong> {escape_html(sender)}</p>"
		f"<p><strong>Organization:</strong> {escape_html(org_display)}</p>"
		f"<p><strong>Subject:</strong> {escape_html(subject)}</p>"
		"<hr>"
		f"<p>{escape_html(message).replace(chr(10), '<br>')}</p>"
	)
	return html, text


def _notify(doc, reply_to: str) -> None:
	recipients = _notify_recipients()
	if not recipients:
		return
	try:
		frappe.sendmail(
			recipients=recipients,
			reply_to=reply_to,
			subject=f"Website enquiry: {doc.subject}",
			content=doc.content,
			reference_doctype=doc.doctype,
			reference_name=doc.name,
		)
	except Exception:
		frappe.log_error(title="Website enquiry notify failed")


def _notify_recipients() -> list[str]:
	settings = frappe.get_single("Site Settings")
	out = []
	for value in (settings.email, settings.communications_email):
		address = cstr(value).strip()
		if address and address not in out:
			out.append(address)
	return out
