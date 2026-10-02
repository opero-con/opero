import frappe
from frappe.tests.utils import FrappeTestCase

from opero.opero_site.load import load_files
from opero.opero_site.publish import content_path_for, settle_publish_statuses


def make_publication(title: str, **fields):
	return frappe.get_doc(
		{
			"doctype": "Publication",
			"title": title,
			"published_on": "2026-08-01",
			"publication_type": "Newsletter",
			"summary": "Summary.",
			**fields,
		}
	).insert(ignore_permissions=True)


class TestPublicationSlugs(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Publication")

	def test_publications_have_ids_independent_of_their_titles(self):
		doc = make_publication("Annual Report")

		self.assertRegex(doc.name, r"^PUB-\d{5}$")
		self.assertEqual(doc.slug, "annual-report")

	def test_duplicate_titles_get_numbered_slugs(self):
		first = make_publication("Annual Report")
		second = make_publication("Annual Report")
		third = make_publication("Annual Report")

		self.assertEqual(
			[first.slug, second.slug, third.slug], ["annual-report", "annual-report-2", "annual-report-3"]
		)
		self.assertEqual(second.title, "Annual Report")

	def test_a_typed_slug_that_is_taken_is_refused(self):
		make_publication("Annual Report")

		with self.assertRaisesRegex(frappe.ValidationError, "already uses the slug annual-report"):
			make_publication("Another Report", slug="Annual Report")

	def test_a_draft_can_change_its_slug(self):
		doc = make_publication("Annual Report")
		doc.slug = "annual-report-2026"
		doc.save(ignore_permissions=True)

		self.assertEqual(frappe.db.get_value("Publication", doc.name, "slug"), "annual-report-2026")
		self.assertEqual(content_path_for(doc), "content/publications/annual-report-2026.md")

	def test_a_live_publication_keeps_its_slug(self):
		doc = make_publication("Annual Report", show_on_website=1)
		settle_publish_statuses()
		doc.reload()
		doc.slug = "annual-report-2026"

		with self.assertRaisesRegex(frappe.ValidationError, "slug can't change"):
			doc.save(ignore_permissions=True)

	def test_the_slug_field_locks_in_the_form_while_live(self):
		field = frappe.get_meta("Publication").get_field("slug")

		self.assertIn("Published", field.read_only_depends_on)
		self.assertTrue(field.unique)

	def test_loading_from_the_website_updates_the_record_with_that_slug(self):
		existing = make_publication("Annual Report")
		text = "---\nslug: annual-report\ntitle: Annual Report 2026\npublishedAt: 2026-08-01\ntype: Newsletter\nsummary: Loaded.\n---\n"

		load_files({"content/publications/annual-report.md": text})

		self.assertEqual(frappe.get_all("Publication", pluck="name"), [existing.name])
		self.assertEqual(frappe.db.get_value("Publication", existing.name, "title"), "Annual Report 2026")
