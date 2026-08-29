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


def apply_publish_status(doc, *, default: str = DRAFT) -> None:
	previous = None if doc.is_new() else doc.get_doc_before_save()
	was_unpublish = cint(previous.unpublish) if previous else 0
	if cint(doc.unpublish) and not was_unpublish:
		if cstr(doc.status) != UNPUBLISHED:
			doc.status = TO_UNPUBLISH
	elif not cint(doc.unpublish) and was_unpublish:
		if cstr(doc.status) != PUBLISHED:
			doc.status = TO_PUBLISH
	elif cstr(doc.status) not in STATUSES:
		doc.status = default
	doc.unpublish = 1 if is_off_site(doc) else 0


def is_to_publish(doc) -> bool:
	return cstr(doc.status) == TO_PUBLISH


def is_to_unpublish(doc) -> bool:
	return cstr(doc.status) == TO_UNPUBLISH


def is_on_site(doc) -> bool:
	return cstr(doc.status) in ON_SITE


def is_off_site(doc) -> bool:
	return cstr(doc.status) in OFF_SITE
