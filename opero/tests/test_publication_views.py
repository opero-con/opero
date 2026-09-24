"""Website view counts on Publication: atomic increments and what they must not touch."""

import frappe
from frappe.exceptions import DoesNotExistError, PermissionError
from frappe.tests.utils import FrappeTestCase

from opero.opero_site.views import get_views, record_view

LIVE = "view-count-live"
DRAFT = "view-count-draft"


def _make_publication(title: str, status: str):
	doc = frappe.get_doc(
		{
			"doctype": "Publication",
			"title": title,
			"published_on": "2025-02-01",
			"publication_type": "Digest",
			"summary": "Used to test view counts.",
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.set_value("Publication", doc.name, "status", status, update_modified=False)
	return doc.name


class TestPublicationViews(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		for name in (LIVE, DRAFT):
			frappe.db.delete("Publication", {"name": name})
		self.live = _make_publication("View count live", "Published")
		self.draft = _make_publication("View count draft", "Draft")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_views_is_a_read_only_counter_that_starts_at_zero(self):
		field = frappe.get_meta("Publication").get_field("views")
		self.assertEqual(field.fieldtype, "Int")
		self.assertTrue(field.read_only)
		self.assertTrue(field.no_copy)
		self.assertEqual(frappe.db.get_value("Publication", self.live, "views"), 0)

	def test_web_views_sits_in_its_own_column(self):
		meta = frappe.get_meta("Publication")
		self.assertEqual(meta.get_field("views").label, "Web Views")
		order = [field.fieldname for field in meta.fields]
		self.assertEqual(meta.get_field(order[order.index("views") - 1]).fieldtype, "Column Break")

	def test_record_view_adds_one_and_returns_the_total(self):
		self.assertEqual(record_view(LIVE), {"views": 1})
		self.assertEqual(record_view(LIVE), {"views": 2})
		self.assertEqual(frappe.db.get_value("Publication", LIVE, "views"), 2)

	def test_record_view_does_not_touch_modified_or_version_history(self):
		before = frappe.db.get_value("Publication", LIVE, "modified")
		versions = frappe.db.count("Version", {"docname": LIVE})
		record_view(LIVE)
		self.assertEqual(frappe.db.get_value("Publication", LIVE, "modified"), before)
		self.assertEqual(frappe.db.count("Version", {"docname": LIVE}), versions)

	def test_record_view_rejects_drafts_unknown_slugs_and_blanks(self):
		for slug in (DRAFT, "no-such-publication", "", "   "):
			with self.assertRaises(DoesNotExistError):
				record_view(slug)
		self.assertEqual(frappe.db.get_value("Publication", DRAFT, "views"), 0)

	def test_guests_cannot_record_or_read_views(self):
		frappe.set_user("Guest")
		with self.assertRaises(PermissionError):
			record_view(LIVE)
		with self.assertRaises(PermissionError):
			get_views()

	def test_get_views_lists_published_publications_only(self):
		record_view(LIVE)
		record_view(LIVE)
		views = get_views()["views"]
		self.assertEqual(views[LIVE], 2)
		self.assertNotIn(DRAFT, views)

	def test_saving_a_stale_form_does_not_reset_the_count(self):
		stale = frappe.get_doc("Publication", LIVE)
		record_view(LIVE)
		record_view(LIVE)
		stale.summary = "Edited while visitors were reading."
		stale.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Publication", LIVE, "views"), 2)

	def test_views_is_not_published_to_the_content_repository(self):
		record_view(LIVE)
		doc = frappe.get_doc("Publication", LIVE)
		self.assertNotIn("views", doc.to_site_frontmatter())
