"""Publish Opero Site DocTypes into opero-content Markdown."""

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.opero_site.github import ContentRepo, changed_files, deleted_managed_files
from opero.opero_site.markdown import to_markdown
from opero.opero_site.publish import collect_content_files, pending_entries, record_publish


class TestOperoSitePublish(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Opero Site Publication")
		frappe.db.delete("Opero Site Team Member")
		publisher = frappe.get_single("Opero Site Publisher")
		publisher.set("publish_log", [])
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

	def test_record_publish_keeps_last_ten_newest_first(self):
		for index in range(12):
			record_publish(
				f"https://github.com/opero-con/opero-content/commit/{index}",
				str(index),
				[(f"content/team/{index}.md", "body")],
			)
		rows = frappe.get_single("Opero Site Publisher").publish_log
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

	def test_collect_includes_team_and_settings_paths(self):
		settings = frappe.get_single("Opero Site Settings")
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
				"doctype": "Opero Site Team Member",
				"member_name": "Anita Onyango",
				"role": "Communications",
				"show_on_website": 1,
				"sort_order": 10,
			}
		).insert(ignore_permissions=True)
		paths = [path for path, _content in collect_content_files()]
		self.assertIn("content/settings/general.md", paths)
		self.assertIn("content/team/anita-onyango.md", paths)

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
