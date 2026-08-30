from __future__ import annotations

from frappe.utils import cint, cstr

DRAFT = "Draft"
TO_PUBLISH = "To publish"
PUBLISHED = "Published"
TO_UNPUBLISH = "To unpublish"
UNPUBLISHED = "Unpublished"
STATUSES = (DRAFT, TO_PUBLISH, PUBLISHED, TO_UNPUBLISH, UNPUBLISHED)
ON_SITE = (TO_PUBLISH, PUBLISHED)
OFF_SITE = (TO_UNPUBLISH, UNPUBLISHED)
ALWAYS_ON_SITE = frozenset({"Home Page", "Privacy", "Site Settings"})


def apply_publish_status(doc, *, default: str = DRAFT) -> None:
	if doc.doctype in ALWAYS_ON_SITE:
		_apply_always_on_site(doc, default=default)
		return
	previous = None if doc.is_new() else doc.get_doc_before_save()
	prev_status = cstr(previous.status) if previous else ""
	current = cstr(doc.status)
	if current not in STATUSES:
		current = prev_status if prev_status in STATUSES else default
		doc.status = current
	if cint(doc.show_on_website):
		doc.status = PUBLISHED if PUBLISHED in (current, prev_status) else TO_PUBLISH
	elif UNPUBLISHED in (current, prev_status):
		doc.status = UNPUBLISHED
	elif PUBLISHED in (current, prev_status) or TO_UNPUBLISH in (current, prev_status):
		doc.status = TO_UNPUBLISH
	else:
		doc.status = DRAFT
	doc.show_on_website = 1 if is_on_site(doc) else 0


def _apply_always_on_site(doc, *, default: str) -> None:
	previous = None if doc.is_new() else doc.get_doc_before_save()
	prev_status = cstr(previous.status) if previous else ""
	current = cstr(doc.status)
	if current not in STATUSES:
		current = prev_status if prev_status in STATUSES else default
	doc.status = PUBLISHED if PUBLISHED in (current, prev_status) else TO_PUBLISH


def is_to_publish(doc) -> bool:
	return cstr(doc.status) == TO_PUBLISH


def is_to_unpublish(doc) -> bool:
	return cstr(doc.status) == TO_UNPUBLISH


def is_on_site(doc) -> bool:
	return doc.doctype in ALWAYS_ON_SITE or cstr(doc.status) in ON_SITE


def is_off_site(doc) -> bool:
	if doc.doctype in ALWAYS_ON_SITE:
		return False
	return cstr(doc.status) in OFF_SITE
