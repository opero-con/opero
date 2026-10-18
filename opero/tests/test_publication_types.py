"""Editors add, rename, merge and delete Publication Types from the Desk."""

import frappe
from frappe.exceptions import LinkExistsError, LinkValidationError
from frappe.model.rename_doc import rename_doc
from frappe.tests.utils import FrappeTestCase

from opero.opero_site.load import load_files
from opero.opero_site.publish_status import PUBLISHED, TO_UPDATE
from opero.opero_site.utils import PRODUCT_PUBLICATION_TYPE
from opero.patches.v0_4.add_product_publication_type import execute as add_product_publication_type

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


def _ensure_type(title: str) -> str:
	if frappe.db.exists("Publication Type", title):
		return title
	return _make_type(title)


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

	def test_page_url_shows_only_for_product(self):
		frappe.reload_doc("opero_site", "doctype", "publication")
		field = frappe.get_meta("Publication").get_field("page_url")
		self.assertEqual(field.depends_on, "eval:doc.publication_type=='Product'")

	def test_non_product_clears_page_url(self):
		_make_type(SLIDES)
		name = _make_publication("Type test slides", SLIDES)
		doc = frappe.get_doc("Publication", name)
		doc.page_url = "/gulper.html"
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.page_url, "")
		self.assertNotIn("pageUrl", doc.to_site_frontmatter())

	def test_product_clears_its_date(self):
		_ensure_type(PRODUCT_PUBLICATION_TYPE)
		name = _make_publication("Type test dated product", PRODUCT_PUBLICATION_TYPE)
		doc = frappe.get_doc("Publication", name)
		doc.published_on = "2024-04-09"
		doc.save(ignore_permissions=True)
		self.assertFalse(doc.published_on)
		self.assertFalse(doc.year)
		self.assertNotIn("publishedAt", doc.to_site_frontmatter())

	def test_product_keeps_page_url(self):
		_ensure_type(PRODUCT_PUBLICATION_TYPE)
		name = _make_publication("Type test product", PRODUCT_PUBLICATION_TYPE)
		doc = frappe.get_doc("Publication", name)
		doc.page_url = "/gulper.html"
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.page_url, "/gulper.html")
		self.assertEqual(doc.to_site_frontmatter()["pageUrl"], "/gulper.html")

	def test_product_type_patch_retypes_technology_pages(self):
		_ensure_type("Overview")
		created = []
		previous = {}
		try:
			for slug in ("gulper", "pitvaq", "pupu-pump"):
				name = frappe.db.get_value("Publication", {"slug": slug})
				if name:
					previous[name] = frappe.db.get_value(
						"Publication",
						name,
						["publication_type", "page_url", "published_on", "year", "status", "show_on_website"],
						as_dict=True,
					)
				else:
					doc = frappe.get_doc(
						{
							"doctype": "Publication",
							"title": f"Type test {slug}",
							"slug": slug,
							"published_on": "2024-04-09",
							"publication_type": "Overview",
							"summary": "Technology page.",
						}
					).insert(ignore_permissions=True)
					created.append(doc.name)
					name = doc.name
				frappe.db.set_value(
					"Publication",
					name,
					{
						"publication_type": "Overview",
						"page_url": f"/{slug}.html",
						"status": PUBLISHED,
						"show_on_website": 1,
					},
					update_modified=False,
				)
			add_product_publication_type()
			for slug in ("gulper", "pitvaq", "pupu-pump"):
				doc = frappe.get_doc("Publication", {"slug": slug})
				self.assertEqual(doc.publication_type, PRODUCT_PUBLICATION_TYPE)
				self.assertEqual(doc.page_url, f"/{slug}.html")
				self.assertFalse(doc.published_on)
				self.assertFalse(doc.year)
				self.assertNotIn("publishedAt", doc.to_site_frontmatter())
				self.assertEqual(doc.status, TO_UPDATE)
			self.assertEqual(
				frappe.db.get_value("Publication Type", "Overview", "description"),
				"A shareable overview, such as the Opero Project Portfolio PDF.",
			)
		finally:
			for name in created:
				frappe.delete_doc("Publication", name, ignore_permissions=True, force=1)
			for name, row in previous.items():
				frappe.db.set_value("Publication", name, row, update_modified=False)

	def test_load_adds_a_type_the_content_repository_uses(self):
		load_files({"content/publications/test-deck-talk.md": DECK_MD})
		self.assertTrue(frappe.db.exists("Publication Type", DECK))
		self.assertEqual(frappe.db.get_value("Publication", {"slug": "test-deck-talk"}, "publication_type"), DECK)
