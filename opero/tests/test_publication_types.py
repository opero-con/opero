"""Editors add, rename, merge and delete Publication Types from the Desk."""

import frappe
from frappe.exceptions import LinkExistsError, LinkValidationError
from frappe.model.rename_doc import rename_doc
from frappe.tests.utils import FrappeTestCase

from opero.opero_site.load import load_files
from opero.opero_site.publish_status import PUBLISHED, TO_UPDATE

SLIDES = "Test slides"
DECK = "Test deck"

DECK_MD = f"""---
slug: test-deck-talk
title: Test deck talk
publishedAt: 2026-09-09
type: {DECK}
summary: Slides from a webinar.
---
"""


def _make_type(title: str) -> str:
	return (
		frappe.get_doc({"doctype": "Publication Type", "title": title}).insert(ignore_permissions=True).name
	)


def _make_publication(title: str, publication_type: str, status: str = PUBLISHED) -> str:
	doc = frappe.get_doc(
		{
			"doctype": "Publication",
			"title": title,
			"published_on": "2026-09-09",
			"publication_type": publication_type,
			"summary": "Used to test publication types.",
		}
	).insert(ignore_permissions=True)
	frappe.db.set_value("Publication", doc.name, "status", status, update_modified=False)
	return doc.name


class TestPublicationTypes(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Publication", {"title": ["like", "Type test %"]})
		frappe.db.delete("Publication", {"slug": "test-deck-talk"})
		frappe.db.delete("Publication Type", {"name": ["in", [SLIDES, DECK]]})

	def test_type_is_a_link_to_editable_records(self):
		field = frappe.get_meta("Publication").get_field("publication_type")
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Publication Type")
		self.assertTrue(frappe.get_meta("Publication Type").allow_rename)

	def test_added_type_is_published_as_is(self):
		_make_type(SLIDES)
		name = _make_publication("Type test added", SLIDES)
		self.assertEqual(frappe.get_doc("Publication", name).to_site_frontmatter()["type"], SLIDES)

	def test_unknown_type_is_rejected(self):
		with self.assertRaises(LinkValidationError):
			_make_publication("Type test unknown", "No such type")

	def test_type_in_use_cannot_be_deleted(self):
		_make_type(SLIDES)
		_make_publication("Type test in use", SLIDES)
		with self.assertRaises(LinkExistsError):
			frappe.delete_doc("Publication Type", SLIDES)

	def test_unused_type_can_be_deleted(self):
		_make_type(SLIDES)
		frappe.delete_doc("Publication Type", SLIDES)
		self.assertFalse(frappe.db.exists("Publication Type", SLIDES))

	def test_merge_moves_publications_and_queues_only_moved_live_ones(self):
		_make_type(SLIDES)
		_make_type(DECK)
		moved = _make_publication("Type test moved", SLIDES)
		draft = _make_publication("Type test draft", SLIDES, status="Draft")
		already = _make_publication("Type test already", DECK)

		rename_doc("Publication Type", SLIDES, DECK, merge=True)

		self.assertFalse(frappe.db.exists("Publication Type", SLIDES))
		for name in (moved, draft, already):
			self.assertEqual(frappe.db.get_value("Publication", name, "publication_type"), DECK)
		self.assertEqual(frappe.db.get_value("Publication", moved, "status"), TO_UPDATE)
		self.assertEqual(frappe.db.get_value("Publication", draft, "status"), "Draft")
		self.assertEqual(frappe.db.get_value("Publication", already, "status"), PUBLISHED)

	def test_rename_updates_title_and_publications(self):
		_make_type(SLIDES)
		name = _make_publication("Type test renamed", SLIDES)

		rename_doc("Publication Type", SLIDES, DECK)

		self.assertEqual(frappe.db.get_value("Publication Type", DECK, "title"), DECK)
		self.assertEqual(frappe.db.get_value("Publication", name, "publication_type"), DECK)
		self.assertEqual(frappe.db.get_value("Publication", name, "status"), TO_UPDATE)

	def test_load_adds_a_type_the_content_repository_uses(self):
		load_files({"content/publications/test-deck-talk.md": DECK_MD})
		self.assertTrue(frappe.db.exists("Publication Type", DECK))
		self.assertEqual(frappe.db.get_value("Publication", {"slug": "test-deck-talk"}, "publication_type"), DECK)
