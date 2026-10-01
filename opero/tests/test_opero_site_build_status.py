from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.opero_site.build_status import refresh_build_statuses, website_status_for
from opero.opero_site.github import GithubError
from opero.opero_site.publish import record_deploy


class _FakeChecksRepo:
	def __init__(self, runs=None, error=False):
		self.runs = runs or {}
		self.error = error
		self.asked = []

	def get_check_run(self, sha, name):
		self.asked.append((sha, name))
		if self.error:
			raise GithubError("GitHub GET failed (403).")
		return self.runs.get(sha)


class TestOperoSiteBuildStatus(FrappeTestCase):
	def setUp(self):
		doc = frappe.get_single("Deploy Center")
		doc.set("deploy_log", [])
		doc.save(ignore_permissions=True)
		frappe.db.delete("Notification Log", {"document_type": "Deploy Center"})
		# Other installed apps act on every new Notification Log; keep them out of these tests.
		hooks = {key: value for key, value in frappe.get_doc_hooks().items() if key != "Notification Log"}
		patcher = patch("frappe.get_doc_hooks", return_value=hooks)
		patcher.start()
		self.addCleanup(patcher.stop)

	def deploy(self, sha):
		record_deploy(
			f"https://github.com/opero-con/opero-content/commit/{sha}", sha, [("content/a.md", "a")]
		)

	def refresh(self, repo):
		with patch("opero.opero_site.build_status.content_repo_from_conf", return_value=repo):
			refresh_build_statuses()
		return {row.sha: row for row in frappe.get_single("Deploy Center").deploy_log}

	def test_website_status_follows_the_deploy_check(self):
		self.assertEqual(website_status_for(None), "Building")
		self.assertEqual(website_status_for({"status": "in_progress"}), "Building")
		self.assertEqual(website_status_for({"status": "completed", "conclusion": "success"}), "Live")
		self.assertEqual(website_status_for({"status": "completed", "conclusion": "failure"}), "Failed")
		self.assertEqual(website_status_for({"status": "completed", "conclusion": "cancelled"}), "Failed")

	def test_new_deploys_start_building_and_older_rows_keep_their_status(self):
		self.deploy("aaa")
		self.refresh(
			_FakeChecksRepo({"aaa": {"status": "completed", "conclusion": "success", "html_url": "u"}})
		)
		self.deploy("bbb")
		rows = frappe.get_single("Deploy Center").deploy_log
		self.assertEqual(
			[(row.sha, row.website_status) for row in rows], [("bbb", "Building"), ("aaa", "Live")]
		)
		self.assertEqual(rows[1].build_url, "u")

	def test_failed_build_is_recorded_and_the_deployer_is_alerted(self):
		self.deploy("bad")
		self.deploy("good")
		self.deploy("slow")
		repo = _FakeChecksRepo(
			{
				"bad": {
					"status": "completed",
					"conclusion": "failure",
					"html_url": "https://github.com/run/1",
				},
				"good": {
					"status": "completed",
					"conclusion": "success",
					"html_url": "https://github.com/run/2",
				},
				"slow": {"status": "in_progress"},
			}
		)
		rows = self.refresh(repo)
		self.assertEqual(rows["bad"].website_status, "Failed")
		self.assertEqual(rows["bad"].build_url, "https://github.com/run/1")
		self.assertEqual(rows["good"].website_status, "Live")
		self.assertEqual(rows["slow"].website_status, "Building")
		self.assertEqual({name for _sha, name in repo.asked}, {"deploy"})
		alerts = frappe.get_all(
			"Notification Log", filters={"document_type": "Deploy Center"}, pluck="subject"
		)
		self.assertEqual(len(alerts), 1)
		self.assertIn("bad", alerts[0])

		self.refresh(repo)
		self.assertEqual(frappe.db.count("Notification Log", {"document_type": "Deploy Center"}), 1)
		self.assertEqual([sha for sha, _name in repo.asked[3:]], ["slow"])

	def test_github_errors_leave_deploys_building(self):
		self.deploy("aaa")
		with patch("opero.opero_site.build_status.frappe.log_error") as log_error:
			rows = self.refresh(_FakeChecksRepo(error=True))
		self.assertEqual(rows["aaa"].website_status, "Building")
		log_error.assert_called_once()

	def test_nothing_building_needs_no_github_token(self):
		self.deploy("aaa")
		frappe.db.set_value("Deploy Log", {"sha": "aaa"}, "website_status", "Live")
		with patch("opero.opero_site.build_status.content_repo_from_conf") as repo:
			refresh_build_statuses()
		repo.assert_not_called()
