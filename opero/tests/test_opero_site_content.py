"""Opero Site content DocTypes: slug, URL, and opero-content frontmatter contract."""

import frappe
from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase

from opero.opero_site.utils import parse_links, slugify


class TestOperoSiteContent(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Opero Site Publication")

	def test_slugify_matches_content_filenames(self):
		self.assertEqual(slugify("January 2025 Update"), "january-2025-update")
		self.assertEqual(slugify("PuPu Pump Digest: Tackling Trash"), "pupu-pump-digest-tackling-trash")

	def test_parse_links_requires_label_and_url(self):
		self.assertEqual(
			parse_links("Portfolio PDF | https://opero-services.com/downloads/portfolio.pdf"),
			[{"label": "Portfolio PDF", "href": "https://opero-services.com/downloads/portfolio.pdf"}],
		)
		with self.assertRaises(ValidationError):
			parse_links("https://example.com")

	def test_settings_frontmatter_matches_general_collection(self):
		doc = frappe.get_single("Opero Site Settings")
		doc.update(
			{
				"organization_name": "Opero Services Ltd",
				"email": "info@opero-services.com",
				"communications_email": "comms@opero-services.com",
				"phone": "+254 115 816297",
				"training_phone": "+254 726 244882",
				"linkedin_url": "https://www.linkedin.com/company/opero-services",
				"twitter_url": "https://twitter.com/OPERO_KE",
				"seo_title": "Opero | Scaling WASH Enterprise and Innovation",
				"seo_description": "Opero scales WASH enterprises across East Africa.",
				"canonical_url": "https://opero-services.com",
			}
		)
		doc.set("offices", [])
		doc.append(
			"offices",
			{
				"office_label": "Nairobi Office",
				"building": "Wood Avenue Plaza, 9th floor",
				"street": "Off Argwings Kodhek Road",
				"city": "Nairobi",
				"country": "Kenya",
			},
		)
		doc.save(ignore_permissions=True)
		self.assertEqual(
			doc.to_site_frontmatter(),
			{
				"organizationName": "Opero Services Ltd",
				"email": "info@opero-services.com",
				"communicationsEmail": "comms@opero-services.com",
				"phone": "+254 115 816297",
				"trainingPhone": "+254 726 244882",
				"offices": [
					{
						"label": "Nairobi Office",
						"building": "Wood Avenue Plaza, 9th floor",
						"street": "Off Argwings Kodhek Road",
						"city": "Nairobi",
						"country": "Kenya",
					}
				],
				"seo": {
					"title": "Opero | Scaling WASH Enterprise and Innovation",
					"description": "Opero scales WASH enterprises across East Africa.",
					"canonicalUrl": "https://opero-services.com",
				},
				"linkedinUrl": "https://www.linkedin.com/company/opero-services",
				"twitterUrl": "https://twitter.com/OPERO_KE",
			},
		)

	def test_settings_reject_invalid_url(self):
		doc = frappe.get_single("Opero Site Settings")
		doc.organization_name = "Opero"
		doc.email = "info@opero-services.com"
		doc.communications_email = "comms@opero-services.com"
		doc.phone = "+254 115 816297"
		doc.linkedin_url = "linkedin.com/company/opero-services"
		with self.assertRaises(ValidationError):
			doc.save(ignore_permissions=True)

	def test_home_frontmatter_omits_team_and_hides_inactive_partners(self):
		doc = frappe.get_single("Opero Site Home")
		doc.hero_eyebrow = "Scaling WASH"
		doc.hero_title = "From idea to lasting WASH impact."
		doc.hero_description = "Practical support for WASH enterprises."
		doc.about_title = "Practical WASH solutions"
		doc.set("about_paragraphs", [])
		doc.append("about_paragraphs", {"paragraph": "Opero is a Kenyan WASH firm."})
		doc.set("pillars", [])
		doc.append("pillars", {"title": "Market research", "description": "Local market realities."})
		doc.set("impacts", [])
		doc.append("impacts", {"value": "6", "metric_label": "WASH technologies designed"})
		doc.set("projects", [])
		doc.append(
			"projects",
			{
				"slug": "pupu-pump",
				"title": "PuPu Pump",
				"short_title": "PuPu",
				"eyebrow": "Sanitation",
				"summary": "Pit-emptying pump.",
				"highlights": "Trash handling\nThick sludge",
				"metric_value": "3",
				"metric_label": "Technologies covered",
				"detail_url": "https://opero-services.com/pupu-pump",
			},
		)
		doc.set("partners", [])
		doc.append(
			"partners",
			{
				"partner_name": "Hidden Partner",
				"show_on_website": 0,
				"sort_order": 1,
			},
		)
		doc.append(
			"partners",
			{
				"partner_name": "Practica Foundation",
				"url": "https://www.practica.org",
				"show_on_website": 1,
				"sort_order": 20,
			},
		)
		doc.save(ignore_permissions=True)
		payload = doc.to_site_frontmatter()
		self.assertNotIn("team", payload)
		self.assertEqual(payload["hero"]["title"], "From idea to lasting WASH impact.")
		self.assertEqual(payload["about"]["paragraphs"], ["Opero is a Kenyan WASH firm."])
		self.assertEqual(payload["pillars"][0]["title"], "Market research")
		self.assertEqual(payload["impacts"][0], {"value": "6", "label": "WASH technologies designed"})
		self.assertEqual(payload["projects"][0]["highlights"], ["Trash handling", "Thick sludge"])
		self.assertEqual(payload["projects"][0]["metricValue"], "3")
		self.assertEqual(payload["partners"], [{"name": "Practica Foundation", "url": "https://www.practica.org"}])

	def test_publication_slug_and_body_frontmatter(self):
		doc = frappe.get_doc(
			{
				"doctype": "Opero Site Publication",
				"title": "January 2025 Update",
				"published_at": "2025-01-30",
				"publication_type": "Newsletter",
				"summary": "A recap of Opero's late-2024 work.",
				"featured": 1,
				"topics": [{"topic": "Company update"}, {"topic": "Projects"}],
				"body": [
					{
						"heading": "What we learned",
						"paragraphs": "First paragraph.\n\nSecond paragraph.",
						"bullets": "Trash in pits\nThick sludge",
						"links": "Portfolio PDF | https://opero-services.com/downloads/portfolio.pdf",
					}
				],
			}
		)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.slug, "january-2025-update")
		self.assertEqual(doc.name, "january-2025-update")
		self.assertEqual(doc.year, 2025)
		self.assertEqual(
			doc.to_site_frontmatter(),
			{
				"slug": "january-2025-update",
				"title": "January 2025 Update",
				"publishedAt": "2025-01-30",
				"type": "Newsletter",
				"summary": "A recap of Opero's late-2024 work.",
				"topics": ["Company update", "Projects"],
				"featured": True,
				"year": 2025,
				"body": [
					{
						"heading": "What we learned",
						"paragraphs": ["First paragraph.", "Second paragraph."],
						"bullets": ["Trash in pits", "Thick sludge"],
						"links": [
							{
								"label": "Portfolio PDF",
								"href": "https://opero-services.com/downloads/portfolio.pdf",
							}
						],
					}
				],
			},
		)

	def test_publication_rejects_invalid_file_url(self):
		doc = frappe.get_doc(
			{
				"doctype": "Opero Site Publication",
				"title": "Bad File URL",
				"published_at": "2025-02-01",
				"publication_type": "Digest",
				"summary": "Should not save.",
				"file_url": "example.com/file.pdf",
			}
		)
		with self.assertRaises(ValidationError):
			doc.insert(ignore_permissions=True)

	def test_publication_accepts_site_relative_file_url(self):
		doc = frappe.get_doc(
			{
				"doctype": "Opero Site Publication",
				"title": "Portfolio Path",
				"published_at": "2023-01-01",
				"publication_type": "Portfolio",
				"summary": "Relative download path from opero-content.",
				"file_url": "/downloads/opero-project-portfolio.pdf",
			}
		)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.file_url, "/downloads/opero-project-portfolio.pdf")

	def test_privacy_frontmatter_matches_privacy_collection(self):
		doc = frappe.get_single("Opero Site Privacy")
		doc.last_reviewed = "2026-07-23"
		doc.set("sections", [])
		doc.append(
			"sections",
			{
				"heading": "Who is responsible",
				"paragraphs": "Opero Services Ltd is the data controller.",
			},
		)
		doc.save(ignore_permissions=True)
		self.assertEqual(
			doc.to_site_frontmatter(),
			{
				"lastReviewed": "2026-07-23",
				"sections": [
					{
						"heading": "Who is responsible",
						"paragraphs": ["Opero Services Ltd is the data controller."],
					}
				],
			},
		)
