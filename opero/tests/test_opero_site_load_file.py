from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.opero_site.load import load_file_from_website
from opero.opero_site.publish import clear_pending_cache, desk_pending_entries, merge_pending_cache
from opero.tests.test_opero_site_load import PRIVACY_MD

PRIVACY_PATH = "content/privacy/privacy.md"
OTHER_PATH = "content/publications/kept-update.md"


class TestLoadFileFromWebsite(FrappeTestCase):
	def setUp(self):
		clear_pending_cache()
		self.addCleanup(clear_pending_cache)
		frappe.db.set_value(
			"Privacy policy", "Privacy policy", {"body": "<p>Old Desk text</p>", "status": "To update"}
		)
		merge_pending_cache(
			[{"path": PRIVACY_PATH, "action": "update"}, {"path": OTHER_PATH, "action": "update"}]
		)
		self.repo = MagicMock(base_branch="main")
		self.repo.get_file.side_effect = lambda path, ref: PRIVACY_MD if path == PRIVACY_PATH else None
		repo_patch = patch("opero.opero_site.load.content_repo_from_conf", return_value=self.repo)
		repo_patch.start()
		self.addCleanup(repo_patch.stop)

	def pending_paths(self):
		return {row["path"] for row in desk_pending_entries()} & {PRIVACY_PATH, OTHER_PATH}

	def test_loads_one_file_and_keeps_other_pending_changes(self):
		result = load_file_from_website(PRIVACY_PATH)

		privacy = frappe.get_single("Privacy policy")
		self.assertIn("Opero Services Ltd is the data controller.", privacy.body)
		self.assertEqual(privacy.status, "Published")
		self.assertEqual(self.pending_paths(), {OTHER_PATH})
		self.assertIn("Loaded", result["message"])

	def test_reports_when_desk_already_matches(self):
		load_file_from_website(PRIVACY_PATH)
		merge_pending_cache([{"path": PRIVACY_PATH, "action": "update"}])

		result = load_file_from_website(PRIVACY_PATH)

		self.assertIn("already matches", result["message"])
		self.assertEqual(self.pending_paths(), {OTHER_PATH})

	def test_refuses_a_file_that_is_not_on_the_website(self):
		with self.assertRaises(frappe.ValidationError):
			load_file_from_website(OTHER_PATH)
		self.assertEqual(self.pending_paths(), {PRIVACY_PATH, OTHER_PATH})

	def test_refuses_paths_outside_website_content(self):
		with self.assertRaises(frappe.ValidationError):
			load_file_from_website("media/homepage/hero.jpg")
		self.repo.get_file.assert_not_called()
