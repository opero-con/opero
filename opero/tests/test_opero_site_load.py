"""Load opero-content Markdown into Opero Site DocTypes."""

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.opero_site.github import ContentRepo, GithubError
from opero.opero_site.load import load_files, slug_from_path
from opero.opero_site.markdown import parse_frontmatter, to_markdown
from opero.tests.website_employee import clear_website_test_employees, make_website_employee

SETTINGS_MD = """---
organizationName: Opero Services Ltd
email: info@opero-services.com
communicationsEmail: comms@opero-services.com
phone: "+254 115 816297"
trainingPhone: "+254 726 244882"
offices:
  - label: Nairobi Office
    building: Wood Avenue Plaza, 9th floor
    street: Off Argwings Kodhek Road
    city: Nairobi
    country: Kenya
linkedinUrl: https://www.linkedin.com/company/opero-services
twitterUrl: https://twitter.com/OPERO_KE
seo:
  title: Opero | Scaling WASH Enterprise and Innovation
  description: Opero scales WASH enterprises across East Africa.
  canonicalUrl: https://opero-services.com
---
"""

HOME_MD = """---
hero:
  eyebrow: Scaling WASH
  title: From idea to lasting WASH impact.
  description: Practical support for WASH enterprises.
  image: /media/homepage/opero-wash-hub.jpg
  imageAlt: Aerial view of WASH work
  note: Kenya · East Africa
  imageFocus: top
  carousel:
    - image: /media/homepage/pupu-pump-team.jpg
      note: Kisumu · Kenya
      imageFocus: left
    - /media/homepage/fecal-sludge-treatment-tower.jpg
about:
  title: Practical WASH solutions
  paragraphs:
    - Opero is a Kenyan WASH firm.
ourWork:
  homepageSummary: To solve WASH challenges.
  pageIntroduction: "To solve WASH challenges, we bring together core expertise in:"
  expertise:
    - title: Market research
      description: Local market realities.
  image: /media/homepage/our-work.jpg
  imageAlt: Opero WASH work in practice
  pageConclusion: Our work is grounded in real operating conditions.
impacts:
  - value: "6"
    label: WASH technologies designed
team:
  - name: Ignored Homepage Team
    role: Should not be imported
---
"""

PRIVACY_MD = """---
lastReviewed: 2026-07-23
sections:
  - heading: Who is responsible
    paragraphs:
      - Opero Services Ltd is the data controller.
    links:
      - label: Privacy mail
        href: https://opero-services.com/privacy
  - heading: Why we use this data
    bullets:
      - Deliver the website
      - Respond to enquiries
---
"""

PUBLICATION_MD = """---
slug: january-2025-update
title: January 2025 Update
publishedAt: 2025-01-30
type: Newsletter
topics:
  - Company update
summary: A recap of Opero's late-2024 work.
featured: true
fileUrl: /downloads/january-2025-update.pdf
body:
  - heading: What we learned
    paragraphs:
      - First paragraph.
      - Second paragraph.
---
"""

PORTFOLIO_MD = """---
slug: opero-project-portfolio
title: Opero Project Portfolio
publishedAt: 2023-01-01
type: Portfolio
topics:
  - Enterprise support
summary: A 22-page overview of Opero's programmes.
featured: true
fileUrl: /downloads/opero-project-portfolio.pdf
---
"""

OVERVIEW_PAGE_MD = """---
slug: pupu-pump
title: PuPu Pump
publishedAt: 2026-07-10
type: Overview
serviceArea: WASH innovation
topics:
  - PuPu Pump
  - Pit emptying
summary: A portable push-pull sanitation pump for pit-latrine emptying.
pageUrl: /pupu-pump.html
---
"""

TEAM_MD = """---
name: Anita Onyango
role: Communications
image: /media/team/anita.jpg
imageAlt: Portrait of Anita Onyango
order: 10
active: true
linkedin: https://www.linkedin.com/in/anita-onyango
---
"""


class TestOperoSiteLoad(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Publication")
		clear_website_test_employees()
		frappe.db.delete("Enterprise")

	def test_parse_frontmatter_and_slug_from_path(self):
		self.assertEqual(parse_frontmatter(TEAM_MD)["name"], "Anita Onyango")
		self.assertEqual(slug_from_path("content/team/anita-onyango.md"), "anita-onyango")
		with self.assertRaises(ValueError):
			parse_frontmatter("no frontmatter here")

	def test_load_maps_content_files_and_ignores_home_team(self):
		member = make_website_employee("Anita Onyango", show_on_website=0)
		counts = load_files(
			{
				"content/settings/general.md": SETTINGS_MD,
				"content/homepage/home.md": HOME_MD,
				"content/privacy/privacy.md": PRIVACY_MD,
				"content/publications/january-2025-update.md": PUBLICATION_MD,
				"content/team/anita-onyango.md": TEAM_MD,
				"docs/editor-guide.md": "---\ntitle: ignored\n---\n",
			}
		)
		self.assertEqual(counts, {"settings": 1, "home": 1, "privacy": 1, "publications": 1, "team": 1, "enterprises": 0})

		settings = frappe.get_single("Site Settings")
		self.assertEqual(settings.organization_name, "Opero Services Ltd")
		self.assertEqual(settings.offices[0].office_label, "Nairobi Office")
		self.assertEqual(settings.seo_title, "Opero | Scaling WASH Enterprise and Innovation")

		hero = frappe.get_single("Hero")
		self.assertEqual(hero.hero_title, "From idea to lasting WASH impact.")
		self.assertEqual(
			[(row.image, row.note, row.image_alt, row.image_focus) for row in hero.hero_images],
			[
				("/media/homepage/opero-wash-hub.jpg", "Kenya · East Africa", "Aerial view of WASH work", "Top"),
				("/media/homepage/pupu-pump-team.jpg", "Kisumu · Kenya", "", "Left"),
				("/media/homepage/fecal-sludge-treatment-tower.jpg", "", "", "Center"),
			],
		)
		home = frappe.get_single("Home Page")
		self.assertEqual(home.to_site_frontmatter()["hero"]["image"], "/media/homepage/opero-wash-hub.jpg")
		self.assertEqual(home.to_site_frontmatter()["hero"]["imageFocus"], "top")
		self.assertEqual(
			home.to_site_frontmatter()["hero"]["carousel"],
			[
				{"image": "/media/homepage/pupu-pump-team.jpg", "note": "Kisumu · Kenya", "imageFocus": "left"},
				{"image": "/media/homepage/fecal-sludge-treatment-tower.jpg"},
			],
		)
		self.assertEqual(frappe.get_single("About").about_body, "<p>Opero is a Kenyan WASH firm.</p>")
		self.assertEqual(
			frappe.get_single("Impacts").impacts[0].metric_label, "WASH technologies designed"
		)
		self.assertEqual(
			frappe.get_single("Our Work").homepage_summary,
			"To solve WASH challenges.",
		)
		self.assertEqual(
			frappe.get_single("Our Work").page_introduction,
			"To solve WASH challenges, we bring together core expertise in:",
		)
		self.assertEqual(
			frappe.get_single("Our Work").page_conclusion,
			"Our work is grounded in real operating conditions.",
		)
		self.assertEqual(frappe.db.count("Employee", {"name": member.name}), 1)

		privacy = frappe.get_single("Privacy policy")
		self.assertEqual(str(privacy.last_reviewed), "2026-07-23")
		self.assertIn("Privacy mail", privacy.body)
		self.assertIn("https://opero-services.com/privacy", privacy.body)
		self.assertIn("Deliver the website", privacy.body)

		publication = frappe.get_doc("Publication", "january-2025-update")
		self.assertEqual(str(publication.published_on), "2025-01-30")
		self.assertEqual(publication.year, 2025)
		self.assertEqual(publication.publication_type, "Newsletter")
		self.assertEqual([row.topic for row in publication.topics], ["Company update"])
		self.assertTrue(frappe.db.exists("Publication Topic", "Company update"))
		self.assertEqual(publication.file_url, "/downloads/january-2025-update.pdf")
		self.assertEqual(
			publication.body,
			"<h2>What we learned</h2><p>First paragraph.</p><p>Second paragraph.</p>",
		)
		self.assertEqual(
			publication.to_site_frontmatter()["body"],
			[
				{
					"heading": "What we learned",
					"paragraphs": ["First paragraph.", "Second paragraph."],
				}
			],
		)

		member.reload()
		self.assertEqual(member.employee_name, "Anita Onyango")
		self.assertEqual(member.portrait, "/media/team/anita.jpg")
		self.assertEqual(member.sort_order, 10)
		self.assertEqual(member.status, "Active")
		self.assertEqual(member.website_status, "Published")
		self.assertTrue(member.show_on_website)
		self.assertEqual(publication.status, "Published")
		self.assertTrue(publication.show_on_website)

	def test_load_maps_portfolio_type_to_overview(self):
		load_files({"content/publications/opero-project-portfolio.md": PORTFOLIO_MD})
		doc = frappe.get_doc("Publication", "opero-project-portfolio")
		self.assertEqual(doc.publication_type, "Overview")
		self.assertEqual(doc.to_site_frontmatter()["type"], "Overview")

	def test_load_maps_overview_page_url(self):
		load_files({"content/publications/pupu-pump.md": OVERVIEW_PAGE_MD})
		doc = frappe.get_doc("Publication", "pupu-pump")
		self.assertEqual(doc.publication_type, "Overview")
		self.assertEqual(doc.page_url, "/pupu-pump.html")
		self.assertEqual(doc.to_site_frontmatter()["pageUrl"], "/pupu-pump.html")

	def test_load_keeps_extra_local_employees(self):
		local = make_website_employee("Local Only", role="Editor", show_on_website=0)
		remote = make_website_employee("Anita Onyango", show_on_website=0)
		load_files({"content/team/anita-onyango.md": TEAM_MD})
		self.assertTrue(frappe.db.exists("Employee", local.name))
		self.assertTrue(frappe.db.exists("Employee", remote.name))

	def test_load_roundtrip_matches_settings_frontmatter(self):
		load_files({"content/settings/general.md": SETTINGS_MD})
		self.assertEqual(
			frappe.get_single("Site Settings").to_site_frontmatter(),
			parse_frontmatter(SETTINGS_MD),
		)

	def test_list_markdown_uses_recursive_tree(self):
		calls = []

		def transport(method, url, json=None):
			calls.append((method, url, json))
			if url.endswith("/commits/main"):
				return {"sha": "base-sha", "commit": {"tree": {"sha": "tree-sha"}}}
			if "git/trees/tree-sha" in url:
				return {
					"truncated": False,
					"tree": [
						{"path": "content/team/anita-onyango.md", "type": "blob"},
						{"path": "content/settings/general.md", "type": "blob"},
						{"path": "docs/editor-guide.md", "type": "blob"},
						{"path": "content/team", "type": "tree"},
					],
				}
			raise AssertionError(url)

		repo = ContentRepo("token", "opero-con/opero-content", transport=transport)
		self.assertEqual(
			repo.list_markdown("content/", "main"),
			["content/team/anita-onyango.md", "content/settings/general.md"],
		)

	def test_list_markdown_fails_when_truncated(self):
		def transport(method, url, json=None):
			if url.endswith("/commits/main"):
				return {"sha": "base-sha", "commit": {"tree": {"sha": "tree-sha"}}}
			return {"truncated": True, "tree": []}

		repo = ContentRepo("token", "opero-con/opero-content", transport=transport)
		with self.assertRaises(GithubError):
			repo.list_markdown("content/", "main")

	def test_markdown_roundtrip_parse(self):
		text = to_markdown({"name": "Anita Onyango", "active": True, "order": 10})
		self.assertEqual(parse_frontmatter(text), {"name": "Anita Onyango", "active": True, "order": 10})

	def test_load_draft_publication_stays_draft(self):
		load_files(
			{
				"content/publications/still-writing.md": """---
title: Still Writing
publishedAt: 2026-08-01
type: Newsletter
summary: Not ready for the public site.
draft: true
---
"""
			}
		)
		doc = frappe.get_doc("Publication", "still-writing")
		self.assertEqual(doc.status, "Draft")
		self.assertFalse(doc.show_on_website)

	def test_load_inactive_employee_is_unpublished(self):
		doc = make_website_employee("Hidden Person", show_on_website=0)
		load_files(
			{
				"content/team/hidden-person.md": """---
name: Hidden Person
role: Editor
order: 99
active: false
---
"""
			}
		)
		doc.reload()
		self.assertEqual(doc.status, "Active")
		self.assertEqual(doc.website_status, "Unpublished")
		self.assertFalse(doc.show_on_website)

	def test_load_enterprise_matches_existing_by_name_and_attaches_logo(self):
		existing = frappe.get_doc(
			{
				"doctype": "Enterprise",
				"enterprise_name": "Gasia Poa",
				"status": "Onboarded",
			}
		).insert(ignore_permissions=True)

		# Minimal valid 1x1 PNG so File.insert can strip EXIF.
		png = (
			b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
			b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
			b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
		)

		class _Repo:
			base_branch = "main"

			def get_bytes(self, path, ref):
				if path != "media/enterprises/gasia-poa.png":
					raise AssertionError(path)
				return png

		counts = load_files(
			{
				"content/enterprises/gasia-poa.md": """---
name: Gasia Poa
order: 10
active: true
logo: /media/enterprises/gasia-poa.png
---
"""
			},
			repo=_Repo(),
		)
		self.assertEqual(counts["enterprises"], 1)
		existing.reload()
		self.assertEqual(existing.status, "Onboarded")
		self.assertEqual(existing.website_status, "Published")
		self.assertTrue(existing.show_on_website)
		self.assertEqual(existing.sort_order, 10)
		self.assertTrue(
			existing.logo.startswith("/files/") or existing.logo.startswith("/private/files/")
		)
		self.assertEqual(frappe.db.count("Enterprise", {"enterprise_name": "Gasia Poa"}), 1)
