from __future__ import annotations

from frappe.utils import cint, cstr

DRAFT = "Draft"
TO_PUBLISH = "To publish"
TO_UNPUBLISH = "To unpublish"
STATUSES = (DRAFT, TO_PUBLISH, TO_UNPUBLISH)
LEGACY_STATUSES = {
	"Published": TO_PUBLISH,
	"Unpublished": TO_UNPUBLISH,
}


def apply_publish_status(doc, *, default: str = DRAFT) -> None:
	previous = None if doc.is_new() else doc.get_doc_before_save()
	was_unpublish = cint(previous.unpublish) if previous else 0
	if cint(doc.unpublish) and not was_unpublish:
		doc.status = TO_UNPUBLISH
	elif not cint(doc.unpublish) and was_unpublish:
		doc.status = TO_PUBLISH
	else:
		doc.status = LEGACY_STATUSES.get(cstr(doc.status), cstr(doc.status))
		if doc.status not in STATUSES:
			doc.status = default
	doc.unpublish = 1 if doc.status == TO_UNPUBLISH else 0


def is_to_publish(doc) -> bool:
	return cstr(doc.status) == TO_PUBLISH


def is_to_unpublish(doc) -> bool:
	return cstr(doc.status) == TO_UNPUBLISH
