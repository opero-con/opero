"""Publish Opero Site DocTypes into opero-content Markdown."""

import base64

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.opero_site.github import ContentRepo, GithubError, changed_files, deleted_managed_files
from opero.opero_site.load import load_files
from opero.opero_site.markdown import parse_frontmatter, preserve_unmanaged_frontmatter, to_markdown
from opero.opero_site.publish import (
	collect_content_files,
	collect_content_plan,
	pending_entries,
	record_deploy,
	settle_publish_statuses,
)
from opero.tests.test_opero_site_load import HOME_MD, PRIVACY_MD, SETTINGS_MD, TEAM_MD

HOME_WITH_TEAM_AND_PARTNERS = """---
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
partners:
  - name: Hidden Partner
    active: false
    order: 1
  - name: Practica Foundation
    url: https://www.practica.org
    active: true
    order: 20
team:
  - name: Ignored Homepage Team
    role: Should not be imported
---
"""

PUBLICATION_WITH_YAML_NOISE = """---
title: January 2025 Update
publishedAt: 2025-01-30T00:00:00Z
type: Newsletter
topics:
  - Company update
summary: "A recap of Opero's late-2024 work."
featured: true
fileUrl: /downloads/january-2025-update.pdf
year: "2025"
draft: false
body:
  - heading: What we learned
    paragraphs:
      - First paragraph.
      - Second paragraph.
---
"""


class TestOperoSitePublish(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Publication")
		frappe.db.delete("Team Member")
		publisher = frappe.get_single("Publisher")
		publisher.set("deploy_log", [])
		publisher.save(ignore_permissions=True)

	def test_pending_entries_marks_deletes(self):
		self.assertEqual(
			pending_entries(
				[
					("content/team/anita-onyango.md", "---\nname: Anita\n---\n"),
					("content/publications/old-update.md", None),
				]
			),
			[
				{"path": "content/team/anita-onyango.md", "action": "update"},
				{"path": "content/publications/old-update.md", "action": "delete"},
			],
		)

	def test_record_deploy_keeps_last_ten_newest_first(self):
		for index in range(12):
			record_deploy(
				f"https://github.com/opero-con/opero-content/commit/{index}",
				str(index),
				[(f"content/team/{index}.md", "body")],
			)
		rows = frappe.get_single("Publisher").deploy_log
		self.assertEqual(len(rows), 10)
		self.assertEqual(rows[0].sha, "11")
		self.assertEqual(rows[0].commit_url, "https://github.com/opero-con/opero-content/commit/11")
		self.assertEqual(rows[-1].sha, "2")
		self.assertEqual(rows[0].file_count, 1)

	def test_markdown_wraps_frontmatter(self):
		text = to_markdown({"name": "Anita Onyango", "active": True, "order": 10})
		self.assertTrue(text.startswith("---\n"))
		self.assertTrue(text.endswith("---\n"))
		self.assertIn("name: Anita Onyango", text)
		self.assertIn("active: true", text)

	def test_changed_files_skips_identical_content(self):
		planned = [("content/team/a.md", "one"), ("content/team/b.md", "two")]
		self.assertEqual(
			changed_files({"content/team/a.md": "one"}, planned),
			[("content/team/b.md", "two")],
		)

	def test_changed_files_skips_load_backup_noise(self):
		github = {
			"content/settings/general.md": SETTINGS_MD,
			"content/homepage/home.md": HOME_WITH_TEAM_AND_PARTNERS,
			"content/privacy/privacy.md": PRIVACY_MD,
			"content/publications/january-2025-update.md": PUBLICATION_WITH_YAML_NOISE,
			"content/team/anita-onyango.md": TEAM_MD,
		}
		load_files(github)
		self.assertEqual(changed_files(github, collect_content_files()), [])

	def test_changed_files_lists_real_desk_edits(self):
		load_files({"content/homepage/home.md": HOME_MD})
		home = frappe.get_single("Home Page")
		home.hero_title = "Edited hero title"
		home.save(ignore_permissions=True)
		changed = changed_files(
			{"content/homepage/home.md": HOME_MD},
			collect_content_files(),
		)
		self.assertTrue(any(path == "content/homepage/home.md" for path, _content in changed))

	def test_preserve_unmanaged_keeps_homepage_team_on_real_edit(self):
		load_files({"content/homepage/home.md": HOME_MD})
		home = frappe.get_single("Home Page")
		home.hero_title = "Edited hero title"
		home.save(ignore_permissions=True)
		planned = dict(collect_content_files())["content/homepage/home.md"]
		merged = preserve_unmanaged_frontmatter(HOME_MD, planned)
		data = parse_frontmatter(merged)
		self.assertEqual(data["hero"]["title"], "Edited hero title")
		self.assertEqual(data["team"][0]["name"], "Ignored Homepage Team")

	def test_collect_includes_team_and_settings_paths(self):
		settings = frappe.get_single("Site Settings")
		settings.update(
			{
				"organization_name": "Opero Services Ltd",
				"email": "info@opero-services.com",
				"communications_email": "comms@opero-services.com",
				"phone": "+254 115 816297",
			}
		)
		settings.save(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Team Member",
				"member_name": "Anita Onyango",
				"role": "Communications",
				"show_on_website": 1,
				"sort_order": 10,
			}
		).insert(ignore_permissions=True)
		paths = [path for path, _content in collect_content_files()]
		self.assertIn("content/settings/general.md", paths)
		self.assertIn("content/team/anita-onyango.md", paths)

	def test_existing_files_reports_progress(self):
		seen = []

		def transport(method, url, json=None):
			if "content%2Fteam%2Fa.md" in url or url.endswith("content/team/a.md?ref=main"):
				return {"content": base64.b64encode(b"one").decode()}
			if "content%2Fteam%2Fb.md" in url or url.endswith("content/team/b.md?ref=main"):
				raise GithubError("GitHub GET failed (404).")
			raise AssertionError(url)

		repo = ContentRepo("token", "opero-con/opero-content", transport=transport)
		found = repo.existing_files(
			["content/team/a.md", "content/team/b.md"],
			"main",
			on_progress=lambda done, total, path: seen.append((done, total, path)),
		)
		self.assertEqual(found, {"content/team/a.md": "one"})
		self.assertEqual(
			seen,
			[(1, 2, "content/team/a.md"), (2, 2, "content/team/b.md")],
		)

	def test_commit_files_updates_main_without_a_pull_request(self):
		calls = []

		def transport(method, url, json=None):
			calls.append((method, url, json))
			if url.endswith("/commits/main"):
				return {"sha": "base-sha", "commit": {"tree": {"sha": "tree-sha"}}}
			if url.endswith("/git/blobs"):
				return {"sha": "blob-sha"}
			if url.endswith("/git/trees"):
				return {"sha": "new-tree"}
			if url.endswith("/git/commits") and method == "POST":
				return {"sha": "commit-sha"}
			if method == "PATCH" and url.endswith("/git/refs/heads/main"):
				return {"object": {"sha": "commit-sha"}}
			raise AssertionError((method, url))

		repo = ContentRepo("token", "opero-con/opero-content", transport=transport)
		result = repo.commit_files(
			[("content/team/anita-onyango.md", "---\nname: Anita\n---\n")],
			message="content: update public site from desk",
		)
		self.assertEqual(result["sha"], "commit-sha")
		self.assertEqual(
			result["html_url"],
			"https://github.com/opero-con/opero-content/commit/commit-sha",
		)
		patch = next(call for call in calls if call[0] == "PATCH")
		self.assertTrue(patch[1].endswith("/git/refs/heads/main"))
		self.assertEqual(patch[2], {"sha": "commit-sha", "force": False})
		self.assertFalse(any("/pulls" in call[1] for call in calls))
		self.assertFalse(any(call[0] == "POST" and call[1].endswith("/git/refs") for call in calls))

	def test_deleted_managed_files_plans_missing_publications_and_team(self):
		planned = [
			"content/settings/general.md",
			"content/homepage/home.md",
			"content/privacy/privacy.md",
			"content/team/anita-onyango.md",
			"content/publications/keep-me.md",
		]
		remote = [
			"content/settings/general.md",
			"content/homepage/home.md",
			"content/privacy/privacy.md",
			"content/team/anita-onyango.md",
			"content/team/gone.md",
			"content/publications/keep-me.md",
			"content/publications/old-update.md",
		]
		self.assertEqual(
			deleted_managed_files(
				planned,
				remote,
				("content/publications/", "content/team/"),
			),
			[
				("content/team/gone.md", None),
				("content/publications/old-update.md", None),
			],
		)
		self.assertEqual(
			deleted_managed_files(
				[],
				[
					"content/settings/general.md",
					"content/homepage/home.md",
					"content/privacy/privacy.md",
					"content/publications/old-update.md",
				],
				("content/publications/", "content/team/"),
			),
			[("content/publications/old-update.md", None)],
		)

	def test_commit_files_sends_null_sha_to_delete(self):
		calls = []

		def transport(method, url, json=None):
			calls.append((method, url, json))
			if url.endswith("/commits/main"):
				return {"sha": "base-sha", "commit": {"tree": {"sha": "tree-sha"}}}
			if url.endswith("/git/blobs"):
				return {"sha": "blob-sha"}
			if url.endswith("/git/trees"):
				return {"sha": "new-tree"}
			if url.endswith("/git/commits") and method == "POST":
				return {"sha": "commit-sha"}
			if method == "PATCH" and url.endswith("/git/refs/heads/main"):
				return {"object": {"sha": "commit-sha"}}
			raise AssertionError((method, url))

		repo = ContentRepo("token", "opero-con/opero-content", transport=transport)
		result = repo.commit_files(
			[
				("content/team/anita-onyango.md", "---\nname: Anita\n---\n"),
				("content/publications/old-update.md", None),
			],
			message="content: update public site from desk",
		)
		self.assertEqual(result["sha"], "commit-sha")
		blob_posts = [call for call in calls if call[0] == "POST" and call[1].endswith("/git/blobs")]
		self.assertEqual(len(blob_posts), 1)
		self.assertEqual(blob_posts[0][2]["content"], "---\nname: Anita\n---\n")
		tree_post = next(call for call in calls if call[0] == "POST" and call[1].endswith("/git/trees"))
		self.assertEqual(
			tree_post[2]["tree"],
			[
				{
					"path": "content/team/anita-onyango.md",
					"mode": "100644",
					"type": "blob",
					"sha": "blob-sha",
				},
				{
					"path": "content/publications/old-update.md",
					"mode": "100644",
					"type": "blob",
					"sha": None,
				},
			],
		)

	def test_new_publication_defaults_to_draft_and_is_kept(self):
		doc = frappe.get_doc(
			{
				"doctype": "Publication",
				"title": "Draft Newsletter",
				"published_on": "2026-08-01",
				"publication_type": "Newsletter",
				"summary": "Still being written in Cubenet.",
			}
		).insert(ignore_permissions=True)
		self.assertEqual(doc.status, "Draft")
		self.assertFalse(doc.show_on_website)
		files, keep = collect_content_plan()
		path = "content/publications/draft-newsletter.md"
		self.assertNotIn(path, dict(files))
		self.assertIn(path, keep)

	def test_published_publication_is_written(self):
		doc = frappe.get_doc(
			{
				"doctype": "Publication",
				"title": "Already Live",
				"published_on": "2026-08-01",
				"publication_type": "Newsletter",
				"summary": "Published stays on-site and is included in the next write.",
				"status": "Published",
				"show_on_website": 1,
			}
		).insert(ignore_permissions=True)
		self.assertEqual(doc.status, "Published")
		self.assertTrue(doc.show_on_website)
		files, keep = collect_content_plan()
		path = "content/publications/already-live.md"
		self.assertIn(path, dict(files))
		self.assertNotIn(path, keep)

	def test_unpublished_publication_is_omitted_for_delete(self):
		doc = frappe.get_doc(
			{
				"doctype": "Publication",
				"title": "Live Then Pulled",
				"published_on": "2026-08-01",
				"publication_type": "Newsletter",
				"summary": "Was live, now unpublished.",
				"status": "Published",
				"show_on_website": 1,
			}
		).insert(ignore_permissions=True)
		doc.show_on_website = 0
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.status, "To unpublish")
		files, keep = collect_content_plan()
		path = "content/publications/live-then-pulled.md"
		self.assertNotIn(path, dict(files))
		self.assertNotIn(path, keep)

	def test_unpublished_team_member_is_written_inactive(self):
		doc = frappe.get_doc(
			{
				"doctype": "Team Member",
				"member_name": "Hidden Editor",
				"role": "Editor",
				"status": "Published",
				"show_on_website": 1,
				"sort_order": 40,
			}
		).insert(ignore_permissions=True)
		doc.show_on_website = 0
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.status, "To unpublish")
		files, _keep = collect_content_plan()
		path = "content/team/hidden-editor.md"
		self.assertIn(path, dict(files))
		self.assertFalse(parse_frontmatter(dict(files)[path])["active"])

	def test_publish_settles_to_publish_to_published(self):
		doc = frappe.get_doc(
			{
				"doctype": "Publication",
				"title": "Ready Newsletter",
				"published_on": "2026-08-01",
				"publication_type": "Newsletter",
				"summary": "Queued, then Publisher marks it live.",
				"show_on_website": 1,
			}
		).insert(ignore_permissions=True)
		self.assertEqual(doc.status, "To publish")
		settle_publish_statuses()
		doc.reload()
		self.assertEqual(doc.status, "Published")
		self.assertTrue(doc.show_on_website)

	def test_publish_settles_to_unpublish_to_unpublished(self):
		doc = frappe.get_doc(
			{
				"doctype": "Publication",
				"title": "Take Me Down",
				"published_on": "2026-08-01",
				"publication_type": "Newsletter",
				"summary": "Queued to come off, then Publisher marks it unpublished.",
				"status": "Published",
				"show_on_website": 1,
			}
		).insert(ignore_permissions=True)
		doc.show_on_website = 0
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.status, "To unpublish")
		settle_publish_statuses()
		doc.reload()
		self.assertEqual(doc.status, "Unpublished")
		self.assertFalse(doc.show_on_website)
		files, keep = collect_content_plan()
		path = "content/publications/take-me-down.md"
		self.assertNotIn(path, dict(files))
		self.assertNotIn(path, keep)

	def test_draft_home_edits_are_kept_not_written(self):
		home = frappe.get_single("Home Page")
		home.db_set("status", "Draft")
		home.db_set("show_on_website", 0)
		home.reload()
		home.hero_title = "Draft hero title"
		home.show_on_website = 0
		home.save(ignore_permissions=True)
		try:
			files, keep = collect_content_plan()
			self.assertNotIn("content/homepage/home.md", dict(files))
			self.assertIn("content/homepage/home.md", keep)
		finally:
			home.show_on_website = 1
			home.save(ignore_permissions=True)

	def test_show_on_website_sets_status(self):
		doc = frappe.get_doc(
			{
				"doctype": "Publication",
				"title": "Checkbox Flow",
				"published_on": "2026-08-01",
				"publication_type": "Newsletter",
				"summary": "Checkbox queues publish; Publisher settles the result.",
			}
		).insert(ignore_permissions=True)
		self.assertEqual(doc.status, "Draft")
		doc.show_on_website = 1
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.status, "To publish")
		settle_publish_statuses()
		doc.reload()
		self.assertEqual(doc.status, "Published")
		self.assertTrue(doc.show_on_website)
		doc.show_on_website = 0
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.status, "To unpublish")
		settle_publish_statuses()
		doc.reload()
		self.assertEqual(doc.status, "Unpublished")
		self.assertFalse(doc.show_on_website)
