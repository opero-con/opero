from __future__ import annotations

import frappe
from frappe import _

from opero.opero_site.github import GithubError
from opero.opero_site.publish import content_repo_from_conf

# Job name in opero-content's deploy.yml; it fails when the Cloudflare build fails.
DEPLOY_CHECK = "deploy"
BUILDING = "Building"
LIVE = "Live"
FAILED = "Failed"


def website_status_for(check_run: dict | None) -> str:
	if not check_run or check_run.get("status") != "completed":
		return BUILDING
	return LIVE if check_run.get("conclusion") == "success" else FAILED


def refresh_build_statuses() -> None:
	"""Settle Building deploys from the website build result on GitHub."""
	rows = frappe.get_all(
		"Deploy Log",
		filters={"parent": "Deploy Center", "website_status": BUILDING},
		fields=["name", "sha", "deployed_by", "commit_url"],
	)
	if not rows:
		return
	repo = content_repo_from_conf()
	for row in rows:
		try:
			check_run = repo.get_check_run(row.sha, DEPLOY_CHECK)
		except GithubError:
			frappe.log_error(title=_("Could not read website build status"))
			return
		settle_deploy(row, website_status_for(check_run), (check_run or {}).get("html_url"))


def settle_deploy(row, status: str, build_url: str | None) -> None:
	if status == BUILDING:
		return
	frappe.db.set_value("Deploy Log", row.name, {"website_status": status, "build_url": build_url})
	if status == FAILED and row.deployed_by:
		notify_failed_deploy(row.deployed_by, row.sha)


def notify_failed_deploy(user: str, sha: str) -> None:
	frappe.get_doc(
		{
			"doctype": "Notification Log",
			"for_user": user,
			"type": "Alert",
			"document_type": "Deploy Center",
			"document_name": "Deploy Center",
			"subject": _(
				"Website deploy {0} failed to build. The site still shows the previous version."
			).format((sha or "")[:7]),
		}
	).insert(ignore_permissions=True)
