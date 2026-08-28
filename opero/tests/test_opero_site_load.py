"""Load opero-content Markdown into Opero Site DocTypes."""

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.opero_site.github import ContentRepo, GithubError
from opero.opero_site.load import load_files, slug_from_path
from opero.opero_site.markdown import parse_frontmatter, to_markdown

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
  imageAlt: Aerial view of WASH work
about:
  title: Practical WASH solutions
  paragraphs:
    - Opero is a Kenyan WASH firm.
pillars:
  - title: Market research
    description: Local market realities.
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
		frappe.db.delete("Team Member")

	def test_parse_frontmatter_and_slug_from_path(self):
		self.assertEqual(parse_frontmatter(TEAM_MD)["name"], "Anita Onyango")
		self.assertEqual(slug_from_path("content/team/anita-onyango.md"), "anita-onyango")
		with self.assertRaises(ValueError):
			parse_frontmatter("no frontmatter here")

	def test_load_maps_content_files_and_ignores_home_team(self):
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
		self.assertEqual(counts, {"settings": 1, "home": 1, "privacy": 1, "publications": 1, "team": 1})

		settings = frappe.get_single("Site Settings")
		self.assertEqual(settings.organization_name, "Opero Services Ltd")
		self.assertEqual(settings.offices[0].office_label, "Nairobi Office")
		self.assertEqual(settings.seo_title, "Opero | Scaling WASH Enterprise and Innovation")

		home = frappe.get_single("Home Page")
		self.assertEqual(home.hero_title, "From idea to lasting WASH impact.")
		self.assertEqual(home.about_paragraphs[0].paragraph, "Opero is a Kenyan WASH firm.")
		self.assertEqual(home.impacts[0].metric_label, "WASH technologies designed")
		self.assertEqual(len(frappe.get_all("Team Member")), 1)

		privacy = frappe.get_single("Privacy")
		self.assertEqual(str(privacy.last_reviewed), "2026-07-23")
		self.assertIn("Privacy mail | https://opero-services.com/privacy", privacy.sections[0].links)
		self.assertEqual(privacy.sections[1].bullets.splitlines()[0], "Deliver the website")

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

		member = frappe.get_doc("Team Member", "anita-onyango")
		self.assertEqual(member.member_name, "Anita Onyango")
		self.assertEqual(member.portrait, "/media/team/anita.jpg")
		self.assertEqual(member.sort_order, 10)
		self.assertEqual(member.status, "To publish")
		self.assertEqual(publication.status, "To publish")

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

	def test_load_keeps_extra_local_team_members(self):
		frappe.get_doc(
			{
				"doctype": "Team Member",
				"member_name": "Local Only",
				"role": "Editor",
				"status": "Draft",
			}
		).insert(ignore_permissions=True)
		load_files({"content/team/anita-onyango.md": TEAM_MD})
		names = set(frappe.get_all("Team Member", pluck="name"))
		self.assertEqual(names, {"local-only", "anita-onyango"})

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
		self.assertFalse(doc.unpublish)

	def test_load_inactive_team_member_is_unpublished(self):
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
		doc = frappe.get_doc("Team Member", "hidden-person")
		self.assertEqual(doc.status, "To unpublish")
		self.assertTrue(doc.unpublish)
