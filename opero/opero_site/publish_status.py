from __future__ import annotations

import frappe
from frappe.utils import cint, cstr

DRAFT = "Draft"
TO_PUBLISH = "To publish"
TO_UPDATE = "To update"
PUBLISHED = "Published"
TO_UNPUBLISH = "To unpublish"
STATUSES = (DRAFT, TO_PUBLISH, TO_UPDATE, PUBLISHED, TO_UNPUBLISH)
QUEUED = (TO_PUBLISH, TO_UPDATE, TO_UNPUBLISH)
ON_SITE = (TO_PUBLISH, TO_UPDATE, PUBLISHED)
LIVE = (TO_UPDATE, PUBLISHED, TO_UNPUBLISH)
ALWAYS_ON_SITE = frozenset({"Home Page", "Our Work", "Privacy policy", "Site Settings"})
# CRM Enterprise keeps `status` for Identified/Onboarded/...; publish sync uses website_status.
PUBLISH_STATUS_FIELD = {
	"Enterprise": "website_status",
	"Employee": "website_status",
	"Partner": "website_status",
}


def publish_status_field(doc_or_doctype) -> str:
	doctype = (
		doc_or_doctype
		if isinstance(doc_or_doctype, str)
		else cstr(getattr(doc_or_doctype, "doctype", ""))
	)
	return PUBLISH_STATUS_FIELD.get(doctype, "status")


def get_publish_status(doc) -> str:
	return cstr(doc.get(publish_status_field(doc)))


def set_publish_status(doc, value: str) -> None:
	doc.set(publish_status_field(doc), value)


def apply_publish_status(doc, *, default: str = DRAFT) -> None:
	if doc.doctype in ALWAYS_ON_SITE:
		_apply_always_on_site(doc, default=default)
		return
	field = publish_status_field(doc)
	previous = None if doc.is_new() else doc.get_doc_before_save()
	prev_status = cstr(previous.get(field)) if previous else ""
	current = cstr(doc.get(field))
	if current not in STATUSES:
		current = prev_status if prev_status in STATUSES else default
		doc.set(field, current)
	# Load from GitHub owns status; Desk save is sync state (pending deploy).
	if frappe.flags.get("opero_site_syncing"):
		doc.show_on_website = 1 if is_on_site(doc) else 0
		return
	doc.set(field, status_for_publish(doc.show_on_website, prev_status or current))
	doc.show_on_website = 1 if is_on_site(doc) else 0


def status_for_publish(publish, saved_status: str) -> str:
	"""Status after the Publish box is set, given the last saved status."""
	is_live = saved_status in LIVE
	if cint(publish):
		return TO_UPDATE if is_live else TO_PUBLISH
	return TO_UNPUBLISH if is_live else DRAFT


def _apply_always_on_site(doc, *, default: str) -> None:
	previous = None if doc.is_new() else doc.get_doc_before_save()
	prev_status = cstr(previous.status) if previous else ""
	current = cstr(doc.status)
	if current not in STATUSES:
		current = prev_status if prev_status in STATUSES else default
		doc.status = current
	# Load from GitHub sets Published and must not re-queue.
	if frappe.flags.get("opero_site_syncing"):
		return
	# Always-on pages are live, so a Desk save queues an update.
	doc.status = TO_UPDATE


def is_queued(doc) -> bool:
	return get_publish_status(doc) in QUEUED


def is_to_unpublish(doc) -> bool:
	return get_publish_status(doc) == TO_UNPUBLISH


def is_on_site(doc) -> bool:
	return doc.doctype in ALWAYS_ON_SITE or get_publish_status(doc) in ON_SITE
