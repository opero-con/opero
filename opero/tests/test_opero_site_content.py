"""Opero Site content DocTypes: slug, URL, and opero-content frontmatter contract."""

import frappe
from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase

from opero.opero_site.body_html import (
	body_sections_to_html,
	dedupe_body_sections,
	html_to_body_sections,
	html_to_paragraphs,
	normalize_body_html,
	normalize_paragraphs_html,
	paragraphs_to_html,
)
from opero.opero_site.utils import normalize_publication_type, parse_links, slugify


class TestOperoSiteContent(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Publication")

	def test_slugify_matches_content_filenames(self):
		self.assertEqual(slugify("January 2025 Update"), "january-2025-update")
		self.assertEqual(slugify("PuPu Pump Digest: Tackling Trash"), "pupu-pump-digest-tackling-trash")

	def test_normalize_publication_type_maps_portfolio_to_overview(self):
		self.assertEqual(normalize_publication_type("Portfolio"), "Overview")
		self.assertEqual(normalize_publication_type("Project"), "Project")
		self.assertEqual(normalize_publication_type(" Case study "), "Case study")

	def test_parse_links_requires_label_and_url(self):
		self.assertEqual(
			parse_links("Portfolio PDF | https://opero-services.com/downloads/portfolio.pdf"),
			[{"label": "Portfolio PDF", "href": "https://opero-services.com/downloads/portfolio.pdf"}],
		)
		with self.assertRaises(ValidationError):
			parse_links("https://example.com")

	def test_settings_frontmatter_matches_general_collection(self):
		doc = frappe.get_single("Site Settings")
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
		doc = frappe.get_single("Site Settings")
		doc.organization_name = "Opero"
		doc.email = "info@opero-services.com"
		doc.communications_email = "comms@opero-services.com"
		doc.phone = "+254 115 816297"
		doc.linkedin_url = "linkedin.com/company/opero-services"
		with self.assertRaises(ValidationError):
			doc.save(ignore_permissions=True)

	def test_home_frontmatter_omits_team_and_hides_inactive_partners(self):
		hero = frappe.get_single("Hero")
		hero.hero_eyebrow = "Scaling WASH"
		hero.hero_title = "From idea to lasting WASH impact."
		hero.hero_description = "Practical support for WASH enterprises."
		hero.set("hero_images", [])
		hero.save(ignore_permissions=True)

		about = frappe.get_single("About")
		about.about_title = "Practical WASH solutions"
		about.about_body = "<p>Opero is a Kenyan WASH firm.</p>"
		about.save(ignore_permissions=True)

		impacts = frappe.get_single("Impacts")
		impacts.set("impacts", [])
		impacts.append("impacts", {"value": "6", "metric_label": "WASH technologies designed"})
		impacts.save(ignore_permissions=True)

		our_work = frappe.get_single("Our Work")
		our_work.set("expertise", [])
		our_work.append("expertise", {"title": "Market research", "description": "Local market realities."})
		our_work.summary = "To solve WASH challenges, we bring together core expertise in technical expertise, enterprise development and market research."
		our_work.image = "/media/homepage/our-work.jpg"
		our_work.image_alt = "Opero WASH work in practice"
		our_work.save(ignore_permissions=True)

		partners = frappe.get_single("Partners")
		partners.set("partners", [])
		partners.append(
			"partners",
			{
				"partner_name": "Hidden Partner",
				"show_on_website": 0,
				"sort_order": 1,
			},
		)
		partners.append(
			"partners",
			{
				"partner_name": "Practica Foundation",
				"url": "https://www.practica.org",
				"show_on_website": 1,
				"sort_order": 20,
			},
		)
		partners.save(ignore_permissions=True)

		payload = frappe.get_single("Home Page").to_site_frontmatter()
		self.assertNotIn("team", payload)
		self.assertNotIn("image", payload["hero"])
		self.assertNotIn("carousel", payload["hero"])
		self.assertNotIn("note", payload["hero"])
		self.assertEqual(payload["hero"]["title"], "From idea to lasting WASH impact.")
		self.assertEqual(payload["about"]["paragraphs"], ["Opero is a Kenyan WASH firm."])
		self.assertEqual(payload["ourWork"]["expertise"][0]["title"], "Market research")
		self.assertEqual(payload["impacts"][0], {"value": "6", "label": "WASH technologies designed"})
		self.assertEqual(payload["ourWork"], {"summary": "To solve WASH challenges, we bring together core expertise in technical expertise, enterprise development and market research.", "expertise": [{"title": "Market research", "description": "Local market realities."}], "image": "/media/homepage/our-work.jpg", "imageAlt": "Opero WASH work in practice"})
		self.assertEqual(payload["partners"], [{"name": "Practica Foundation", "url": "https://www.practica.org"}])

	def test_home_frontmatter_includes_hero_carousel(self):
		doc = frappe.get_single("Hero")
		doc.hero_title = "From idea to lasting WASH impact."
		doc.set("hero_images", [])
		doc.append(
			"hero_images",
			{
				"image": "/media/homepage/opero-wash-hub.jpg",
				"image_alt": "Aerial view of WASH work",
				"note": "Kenya · East Africa",
				"image_focus": "Top",
			},
		)
		doc.append(
			"hero_images",
			{"image": "/media/homepage/pupu-pump-team.jpg", "note": "Kisumu · Kenya", "image_focus": "Left"},
		)
		doc.append(
			"hero_images",
			{"image": "/media/homepage/fecal-sludge-treatment-tower.jpg", "note": "", "image_focus": "Center"},
		)
		doc.save(ignore_permissions=True)
		hero = doc.to_site_frontmatter()
		self.assertEqual(hero["image"], "/media/homepage/opero-wash-hub.jpg")
		self.assertEqual(hero["imageAlt"], "Aerial view of WASH work")
		self.assertEqual(hero["note"], "Kenya · East Africa")
		self.assertEqual(hero["imageFocus"], "top")
		self.assertEqual(
			hero["carousel"],
			[
				{"image": "/media/homepage/pupu-pump-team.jpg", "note": "Kisumu · Kenya", "imageFocus": "left"},
				{"image": "/media/homepage/fecal-sludge-treatment-tower.jpg"},
			],
		)

	def test_publication_slug_and_body_frontmatter(self):
		doc = frappe.get_doc(
			{
				"doctype": "Publication",
				"title": "January 2025 Update",
				"published_on": "2025-01-30",
				"publication_type": "Newsletter",
				"summary": "A recap of Opero's late-2024 work.",
				"featured": 1,
				"topics": [{"topic": "Company update"}, {"topic": "Projects"}],
				"body": (
					"<h2>What we learned</h2>"
					"<p>First paragraph.</p>"
					"<p>Second paragraph.</p>"
					"<ul><li>Trash in pits</li><li>Thick sludge</li></ul>"
					'<p><a href="https://opero-services.com/downloads/portfolio.pdf">Portfolio PDF</a></p>'
				),
			}
		)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.slug, "january-2025-update")
		self.assertEqual(doc.name, "january-2025-update")
		self.assertEqual(doc.year, 2025)
		self.assertTrue(frappe.db.exists("Publication Topic", "Company update"))
		self.assertTrue(frappe.db.exists("Publication Topic", "Projects"))
		self.assertEqual([row.topic for row in doc.topics], ["Company update", "Projects"])
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

	def test_publication_year_derived_from_published_on(self):
		doc = frappe.get_doc(
			{
				"doctype": "Publication",
				"title": "Wrong Year Override",
				"published_on": "2024-06-15",
				"year": 1999,
				"publication_type": "Digest",
				"summary": "Year must come from published_on.",
			}
		)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.year, 2024)
		self.assertEqual(doc.to_site_frontmatter()["year"], 2024)
		self.assertEqual(doc.to_site_frontmatter()["publishedAt"], "2024-06-15")

	def test_publication_rejects_invalid_file_url(self):
		doc = frappe.get_doc(
			{
				"doctype": "Publication",
				"title": "Bad File URL",
				"published_on": "2025-02-01",
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
				"doctype": "Publication",
				"title": "Overview Path",
				"published_on": "2023-01-01",
				"publication_type": "Overview",
				"summary": "Relative download path from opero-content.",
				"file_url": "/downloads/opero-project-portfolio.pdf",
			}
		)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.file_url, "/downloads/opero-project-portfolio.pdf")
		self.assertEqual(doc.publication_type, "Overview")
		self.assertEqual(doc.to_site_frontmatter()["type"], "Overview")
		self.assertNotIn("pageUrl", doc.to_site_frontmatter())

	def test_publication_accepts_desk_file_url(self):
		for title, file_url in (
			("Desk Public Pdf", "/files/january-update.pdf"),
			("Desk Private Pdf", "/private/files/january-update.pdf"),
		):
			doc = frappe.get_doc(
				{
					"doctype": "Publication",
					"title": title,
					"published_on": "2025-02-01",
					"publication_type": "Digest",
					"summary": "Attached from Desk.",
					"file_url": file_url,
				}
			)
			doc.insert(ignore_permissions=True)
			self.assertEqual(doc.file_url, file_url)
			self.assertEqual(doc.to_site_frontmatter()["fileUrl"], file_url)

	def test_publication_overview_page_url_opens_technology_page(self):
		doc = frappe.get_doc(
			{
				"doctype": "Publication",
				"title": "PuPu Pump",
				"published_on": "2026-07-10",
				"publication_type": "Overview",
				"service_area": "WASH innovation",
				"summary": "A portable push-pull sanitation pump for pit-latrine emptying.",
				"page_url": "/pupu-pump.html",
				"topics": [{"topic": "PuPu Pump"}, {"topic": "Pit emptying"}],
			}
		)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.slug, "pupu-pump")
		self.assertEqual(doc.page_url, "/pupu-pump.html")
		self.assertEqual(
			doc.to_site_frontmatter()["pageUrl"],
			"/pupu-pump.html",
		)

	def test_publication_portfolio_alias_saves_as_overview(self):
		doc = frappe.get_doc(
			{
				"doctype": "Publication",
				"title": "Opero Project Portfolio",
				"published_on": "2023-01-01",
				"publication_type": "Portfolio",
				"summary": "Shareable PDF previously typed Portfolio.",
			}
		)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.publication_type, "Overview")
		self.assertEqual(doc.to_site_frontmatter()["type"], "Overview")

	def test_publication_rejects_unknown_type(self):
		doc = frappe.get_doc(
			{
				"doctype": "Publication",
				"title": "Unknown Type",
				"published_on": "2025-01-01",
				"publication_type": "White paper",
				"summary": "Should not save.",
			}
		)
		with self.assertRaises(ValidationError):
			doc.insert(ignore_permissions=True)

	def test_publication_project_with_results_body(self):
		doc = frappe.get_doc(
			{
				"doctype": "Publication",
				"title": "WAKE UP Accelerator programme",
				"published_on": "2022-12-15",
				"publication_type": "Project",
				"service_area": "WASH enterprise",
				"summary": "A sector-specific accelerator for WASH businesses in Kenya.",
				"body": (
					"<p>This work ran from 2021 to 2022.</p>"
					"<h2>Results</h2>"
					"<ul><li>13 WASH businesses trained</li>"
					"<li>$500,000 raised to support the 2021 cohort</li></ul>"
				),
			}
		)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.publication_type, "Project")
		self.assertEqual(
			doc.to_site_frontmatter()["body"],
			[
				{"paragraphs": ["This work ran from 2021 to 2022."]},
				{
					"heading": "Results",
					"bullets": [
						"13 WASH businesses trained",
						"$500,000 raised to support the 2021 cohort",
					],
				},
			],
		)

	def test_privacy_frontmatter_matches_privacy_collection(self):
		doc = frappe.get_single("Privacy policy")
		doc.body = body_sections_to_html(
			[
				{
					"heading": "Who is responsible",
					"paragraphs": ["Opero Services Ltd is the data controller."],
				}
			]
		)
		doc.save(ignore_permissions=True)
		self.assertEqual(str(doc.last_reviewed), frappe.utils.today())
		self.assertEqual(
			doc.to_site_frontmatter(),
			{
				"lastReviewed": frappe.utils.today(),
				"sections": [
					{
						"heading": "Who is responsible",
						"paragraphs": ["Opero Services Ltd is the data controller."],
					}
				],
			},
		)

	def test_privacy_last_reviewed_stays_put_when_body_unchanged(self):
		doc = frappe.get_single("Privacy policy")
		doc.body = body_sections_to_html(
			[{"heading": "Contact", "paragraphs": ["Write to privacy@example.com."]}]
		)
		doc.save(ignore_permissions=True)
		first_reviewed = str(doc.last_reviewed)
		doc.reload()
		doc.status = "To deploy"
		doc.save(ignore_permissions=True)
		self.assertEqual(str(doc.last_reviewed), first_reviewed)

	def test_privacy_load_keeps_frontmatter_last_reviewed(self):
		doc = frappe.get_single("Privacy policy")
		frappe.flags.opero_site_syncing = True
		try:
			doc.last_reviewed = "2026-07-23"
			doc.body = body_sections_to_html(
				[{"heading": "Contact", "paragraphs": ["Write to privacy@example.com."]}]
			)
			doc.save(ignore_permissions=True)
		finally:
			frappe.flags.opero_site_syncing = False
		self.assertEqual(str(doc.last_reviewed), "2026-07-23")


class TestPublicationBodyHtml(FrappeTestCase):
	def test_html_roundtrip_matches_frontmatter_body(self):
		sections = [
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
		]
		html = body_sections_to_html(sections)
		self.assertEqual(html_to_body_sections(html), sections)

	def test_paragraphs_html_roundtrip_matches_about_frontmatter(self):
		paragraphs = ["Opero is a Kenyan WASH firm.", "We design practical tools."]
		html = paragraphs_to_html(paragraphs)
		self.assertEqual(html_to_paragraphs(html), paragraphs)
		self.assertEqual(normalize_paragraphs_html(html + html), paragraphs_to_html(paragraphs))

	def test_html_empty_editor_is_omitted(self):
		self.assertEqual(html_to_body_sections("<p><br></p>"), [])
		self.assertEqual(body_sections_to_html([]), "")

	def test_html_standalone_link_becomes_section_button(self):
		html = (
			"<h2>Takeaway</h2><p>Read more below.</p>"
			'<p><a href="/pupu-pump.html">Explore the PuPu Pump</a></p>'
		)
		self.assertEqual(
			html_to_body_sections(html),
			[
				{
					"heading": "Takeaway",
					"paragraphs": ["Read more below."],
					"links": [{"label": "Explore the PuPu Pump", "href": "/pupu-pump.html"}],
				}
			],
		)

	def test_html_inline_link_stays_in_paragraph_text(self):
		html = '<p>See the <a href="/pupu-pump.html">PuPu Pump</a> page.</p>'
		self.assertEqual(
			html_to_body_sections(html),
			[{"paragraphs": ["See the PuPu Pump page."]}],
		)

	def test_html_rejects_invalid_link_url(self):
		with self.assertRaises(ValidationError):
			html_to_body_sections('<p><a href="example.com/file.pdf">Download</a></p>')

	def test_mirrored_section_list_is_deduped(self):
		section = {
			"heading": "Who is responsible",
			"paragraphs": ["Opero Services Ltd is the data controller."],
		}
		doubled = [section, {"heading": "Why we use this data", "bullets": ["Deliver the website"]}]
		doubled = doubled + doubled
		self.assertEqual(
			dedupe_body_sections(doubled),
			[
				{
					"heading": "Who is responsible",
					"paragraphs": ["Opero Services Ltd is the data controller."],
				},
				{"heading": "Why we use this data", "bullets": ["Deliver the website"]},
			],
		)
		html = body_sections_to_html(doubled)
		self.assertEqual(html.count("<h2>"), 2)
		self.assertEqual(
			normalize_body_html(html + html),
			body_sections_to_html(
				[
					{
						"heading": "Who is responsible",
						"paragraphs": ["Opero Services Ltd is the data controller."],
					},
					{"heading": "Why we use this data", "bullets": ["Deliver the website"]},
				]
			),
		)

	def test_privacy_validate_collapses_mirrored_body(self):
		section_html = body_sections_to_html(
			[
				{
					"heading": "Who is responsible",
					"paragraphs": ["Opero Services Ltd is the data controller."],
				}
			]
		)
		doc = frappe.get_single("Privacy policy")
		doc.last_reviewed = "2026-07-23"
		doc.body = section_html + section_html
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.body, section_html)
		self.assertEqual(
			doc.to_site_frontmatter()["sections"],
			[
				{
					"heading": "Who is responsible",
					"paragraphs": ["Opero Services Ltd is the data controller."],
				}
			],
		)
