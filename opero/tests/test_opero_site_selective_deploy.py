from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.opero_site.markdown import to_markdown
from opero.opero_site.publish import (
	clear_pending_cache,
	deploy_document,
	desk_pending_entries,
	document_deploy_paths,
	notify_pending_website_changes,
	planned_content_changes,
	settle_publish_statuses,
)
from opero.tests.test_opero_site_deploy import _FakeContentRepo


class _CommittingRepo(_FakeContentRepo):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.commits = []

	def commit_files(self, files, message, on_progress=None):
		self.commits.append((files, message))
		return {"sha": "abc123", "html_url": "https://github.com/opero-con/opero-content/commit/abc123"}


def make_publication(title: str, **fields):
	doc = frappe.get_doc(
		{
			"doctype": "Publication",
			"title": title,
			"published_on": "2026-08-01",
			"publication_type": "Newsletter",
			"summary": "Summary.",
			"show_on_website": 1,
			**fields,
		}
	).insert(ignore_permissions=True)
	notify_pending_website_changes(doc, "on_update")
	return doc


def make_live_publication(title: str, **fields):
	doc = make_publication(title, **fields)
	settle_publish_statuses()
	clear_pending_cache()
	doc.reload()
	return doc


class TestSelectiveDeploy(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Publication")
		frappe.db.delete("Partner")
		frappe.db.set_value(
			"Employee", {"slug": ["is", "set"]}, {"show_on_website": 0, "website_status": "Draft"}
		)
		clear_pending_cache()
		self.addCleanup(clear_pending_cache)

	def test_selected_paths_leave_other_queued_changes_on_github(self):
		make_publication("Finished Article")
		make_publication("Trainee Draft")
		pulled = make_live_publication("Pulled Article")
		pulled.show_on_website = 0
		pulled.save(ignore_permissions=True)
		pulled_path = "content/publications/pulled-article.md"
		repo = _FakeContentRepo(
			existing={pulled_path: "---\nslug: pulled-article\n---\n"}, blobs={pulled_path: "a1"}
		)

		files = dict(planned_content_changes(repo, paths=["content/publications/finished-article.md"]))

		self.assertIn("content/publications/finished-article.md", files)
		self.assertNotIn("content/publications/trainee-draft.md", files)
		self.assertNotIn(pulled_path, files)

	def test_selective_deploy_prunes_only_media_the_selection_stopped_using(self):
		make_live_publication("New Cover", cover="/media/publications/new-cover.png")
		path = "content/publications/new-cover.md"
		old = to_markdown({"slug": "new-cover", "cover": "/media/publications/old-cover.png"})
		blobs = {
			path: "a1",
			"media/publications/old-cover.png": "b2",
			"media/publications/new-cover.png": "b3",
			"media/publications/stray.png": "c3",
		}
		repo = _FakeContentRepo(existing={path: old}, blobs=blobs)

		files = planned_content_changes(repo, paths=[path])

		self.assertIn(("media/publications/old-cover.png", None), files)
		self.assertNotIn(("media/publications/stray.png", None), files)

	def test_selective_deploy_keeps_media_an_unselected_live_file_uses(self):
		make_live_publication("Shared Cover")
		make_live_publication("Other Article")
		shared = "/media/publications/shared.png"
		path = "content/publications/shared-cover.md"
		other = "content/publications/other-article.md"
		existing = {
			path: to_markdown({"slug": "shared-cover", "cover": shared}),
			other: to_markdown({"slug": "other-article", "cover": shared}),
		}
		blobs = {path: "a1", other: "a2", "media/publications/shared.png": "b2"}

		files = planned_content_changes(_FakeContentRepo(existing=existing, blobs=blobs), paths=[path])

		self.assertNotIn(("media/publications/shared.png", None), files)

	def test_renamed_record_deploys_its_old_file_with_it(self):
		doc = frappe.get_doc(
			{
				"doctype": "Partner",
				"partner_name": "Practica",
				"website_status": "Published",
				"show_on_website": 1,
			}
		).insert(ignore_permissions=True)
		clear_pending_cache()
		doc.partner_name = "Practica Foundation"
		doc.save(ignore_permissions=True)
		notify_pending_website_changes(doc, "on_update")
		old_path = "content/partners/practica.md"
		new_path = "content/partners/practica-foundation.md"

		paths = document_deploy_paths(doc)
		repo = _FakeContentRepo(existing={old_path: "---\nname: Practica\n---\n"}, blobs={old_path: "a1"})
		files = dict(planned_content_changes(repo, paths=paths))

		self.assertEqual(paths, [old_path, new_path])
		self.assertIsNone(files[old_path])
		self.assertIn(new_path, files)

	def test_deploy_document_settles_only_that_record(self):
		finished = make_publication("Finished Article")
		make_publication("Trainee Draft")
		repo = _CommittingRepo()

		with patch("opero.opero_site.publish.content_repo_from_conf", return_value=repo):
			result = deploy_document("Publication", finished.name)

		[(files, _message)] = repo.commits
		self.assertEqual([path for path, _content in files], ["content/publications/finished-article.md"])
		self.assertEqual(result["sha"], "abc123")
		self.assertEqual(frappe.db.get_value("Publication", finished.name, "status"), "Published")
		self.assertEqual(frappe.db.get_value("Publication", "trainee-draft", "status"), "To publish")
		pending = {row["path"] for row in desk_pending_entries() if row["group"] == "Publications"}
		self.assertEqual(pending, {"content/publications/trainee-draft.md"})

	def test_deploy_document_refuses_non_content_doctypes(self):
		with self.assertRaises(frappe.ValidationError):
			deploy_document("ToDo", "anything")
