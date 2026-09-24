from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.patches.v0_4 import adopt_publish_statuses as patch_module


class FakeRepo:
	base_branch = "main"

	def __init__(self, files):
		self.files = files

	def existing_files(self, paths, ref):
		return {path: self.files[path] for path in paths if path in self.files}


def make_publication(title, status):
	doc = frappe.get_doc(
		{
			"doctype": "Publication",
			"title": title,
			"published_on": "2026-08-01",
			"publication_type": "Newsletter",
			"summary": "Legacy status fixture.",
		}
	).insert(ignore_permissions=True)
	doc.db_set("status", status, update_modified=False)
	return doc


class TestAdoptPublishStatuses(FrappeTestCase):
	def test_legacy_statuses_move_to_the_new_names_without_a_token(self):
		queued = make_publication("Legacy Queued", "To deploy")
		pulled = make_publication("Legacy Pulled", "Unpublished")
		frappe.db.set_single_value("Home Page", "status", "To deploy")
		with patch.dict(frappe.conf, {"opero_content_github_token": None}):
			patch_module.execute()
		self.assertEqual(frappe.db.get_value("Publication", queued.name, "status"), "To update")
		self.assertEqual(frappe.db.get_value("Publication", pulled.name, "status"), "Draft")
		self.assertEqual(frappe.db.get_single_value("Home Page", "status"), "To update")
		self.assertEqual(frappe.get_meta("Employee").get_field("show_on_website").label, "Publish")
		self.assertIn("To update", frappe.get_meta("Employee").get_field("website_status").options)

	def test_queued_records_split_by_what_the_public_site_shows(self):
		live = make_publication("Legacy Live", "To deploy")
		hidden = make_publication("Legacy Hidden", "To deploy")
		new = make_publication("Legacy New", "To deploy")
		repo = FakeRepo(
			{
				"content/publications/legacy-live.md": "---\ntitle: Legacy Live\n---\n",
				"content/publications/legacy-hidden.md": "---\ntitle: Legacy Hidden\ndraft: true\n---\n",
			}
		)
		with (
			patch.dict(frappe.conf, {"opero_content_github_token": "token"}),
			patch.object(patch_module, "content_repo_from_conf", return_value=repo),
		):
			patch_module.execute()
		self.assertEqual(frappe.db.get_value("Publication", live.name, "status"), "To update")
		self.assertEqual(frappe.db.get_value("Publication", hidden.name, "status"), "To publish")
		self.assertEqual(frappe.db.get_value("Publication", new.name, "status"), "To publish")
