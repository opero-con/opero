from __future__ import annotations

import frappe
from frappe.utils import cint, cstr

DRAFT = "Draft"
TO_DEPLOY = "To deploy"
TO_PUBLISH = TO_DEPLOY  # historical patches; prefer TO_DEPLOY in new code
PUBLISHED = "Published"
TO_UNPUBLISH = "To unpublish"
UNPUBLISHED = "Unpublished"
STATUSES = (DRAFT, TO_DEPLOY, PUBLISHED, TO_UNPUBLISH, UNPUBLISHED)
ON_SITE = (TO_DEPLOY, PUBLISHED)
OFF_SITE = (TO_UNPUBLISH, UNPUBLISHED)
ALWAYS_ON_SITE = frozenset({"Home Page", "Our Work", "Privacy policy", "Site Settings"})
# CRM Enterprise keeps `status` for Identified/Onboarded/...; publish sync uses website_status.
PUBLISH_STATUS_FIELD = {
	"Enterprise": "website_status",
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
	if cint(doc.show_on_website):
		doc.set(field, TO_DEPLOY)
	elif UNPUBLISHED in (current, prev_status):
		doc.set(field, UNPUBLISHED)
	elif PUBLISHED in (current, prev_status) or TO_UNPUBLISH in (current, prev_status):
		doc.set(field, TO_UNPUBLISH)
	else:
		doc.set(field, DRAFT)
	doc.show_on_website = 1 if is_on_site(doc) else 0


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
	# Desk save queues a deploy; Status is sync state, not "ever live".
	doc.status = TO_DEPLOY


def is_to_deploy(doc) -> bool:
	return get_publish_status(doc) == TO_DEPLOY


is_to_publish = is_to_deploy  # historical name


def is_to_unpublish(doc) -> bool:
	return get_publish_status(doc) == TO_UNPUBLISH


def is_on_site(doc) -> bool:
	return doc.doctype in ALWAYS_ON_SITE or get_publish_status(doc) in ON_SITE


def is_off_site(doc) -> bool:
	if doc.doctype in ALWAYS_ON_SITE:
		return False
	return get_publish_status(doc) in OFF_SITE
