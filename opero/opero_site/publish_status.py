from __future__ import annotations

from frappe.utils import cint, cstr

DRAFT = "Draft"
PUBLISHED = "Published"
UNPUBLISHED = "Unpublished"
STATUSES = (DRAFT, PUBLISHED, UNPUBLISHED)


def apply_publish_status(doc, *, default: str = DRAFT) -> None:
	previous = None if doc.is_new() else doc.get_doc_before_save()
	was_unpublish = cint(previous.unpublish) if previous else 0
	if cint(doc.unpublish) and not was_unpublish:
		doc.status = UNPUBLISHED
	elif not cint(doc.unpublish) and was_unpublish:
		doc.status = PUBLISHED
	elif cstr(doc.status) not in STATUSES:
		doc.status = default
	doc.unpublish = 1 if doc.status == UNPUBLISHED else 0


def is_published(doc) -> bool:
	return cstr(doc.status) == PUBLISHED


def is_unpublished(doc) -> bool:
	return cstr(doc.status) == UNPUBLISHED
