"""Team Member slug, URL, and content-frontmatter contract."""

import frappe
from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase

from opero.opero_site.utils import slugify


class TestTeamMember(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Team Member")

	def test_slugify_matches_content_filenames(self):
		self.assertEqual(slugify("Nicola Greene"), "nicola-greene")
		self.assertEqual(slugify("  Anita  Onyango "), "anita-onyango")

	def test_slug_is_generated_from_member_name(self):
		doc = self._member(member_name="Nicola Greene", slug="")
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.slug, "nicola-greene")
		self.assertEqual(doc.name, "nicola-greene")

	def test_new_team_member_defaults_to_draft(self):
		doc = frappe.get_doc(
			{
				"doctype": "Team Member",
				"member_name": "New Draft",
				"role": "Editor",
			}
		).insert(ignore_permissions=True)
		self.assertEqual(doc.status, "Draft")
		self.assertFalse(doc.unpublish)

	def test_linkedin_must_be_full_url(self):
		doc = self._member(linkedin="linkedin.com/in/nicolagreene")
		with self.assertRaises(ValidationError):
			doc.insert(ignore_permissions=True)

	def test_frontmatter_matches_site_team_collection(self):
		doc = self._member(
			member_name="Anita Onyango",
			role="Director",
			linkedin="https://www.linkedin.com/in/anita-onyango",
			sort_order=10,
			status="To publish",
			portrait_alt="Portrait of Anita Onyango",
		)
		doc.insert(ignore_permissions=True)
		self.assertEqual(
			doc.to_site_frontmatter(),
			{
				"name": "Anita Onyango",
				"role": "Director",
				"image": "",
				"imageAlt": "Portrait of Anita Onyango",
				"order": 10,
				"active": True,
				"linkedin": "https://www.linkedin.com/in/anita-onyango",
			},
		)

	def _member(self, **fields):
		payload = {
			"doctype": "Team Member",
			"member_name": "Test Member",
			"role": "Water Specialist",
			"status": "To publish",
			"sort_order": 10,
		}
		payload.update(fields)
		return frappe.get_doc(payload)
