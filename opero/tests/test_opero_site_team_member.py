"""Opero Site Team Member slug, URL, and content-frontmatter contract."""

import frappe
from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase

from opero.opero_site.doctype.opero_site_team_member.opero_site_team_member import slugify


class TestOperoSiteTeamMember(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Opero Site Team Member")

	def test_slugify_matches_content_filenames(self):
		self.assertEqual(slugify("Nicola Greene"), "nicola-greene")
		self.assertEqual(slugify("  Anita  Onyango "), "anita-onyango")

	def test_slug_is_generated_from_member_name(self):
		doc = self._member(member_name="Nicola Greene", slug="")
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.slug, "nicola-greene")
		self.assertEqual(doc.name, "nicola-greene")

	def test_linkedin_must_be_https_url(self):
		doc = self._member(linkedin="linkedin.com/in/nicolagreene")
		with self.assertRaises(ValidationError):
			doc.insert(ignore_permissions=True)

	def test_frontmatter_matches_site_team_collection(self):
		doc = self._member(
			member_name="Anita Onyango",
			role="Director",
			linkedin="https://www.linkedin.com/in/anita-onyango",
			sort_order=10,
			show_on_website=1,
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
			"doctype": "Opero Site Team Member",
			"member_name": "Test Member",
			"role": "Water Specialist",
			"show_on_website": 1,
			"sort_order": 10,
		}
		payload.update(fields)
		return frappe.get_doc(payload)
