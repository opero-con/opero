from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

from opero.opero_site.github import ContentRepo, GithubError, changed_files, deleted_managed_files
from opero.opero_site.markdown import to_markdown

DEFAULT_REPO = "opero-con/opero-content"
DEFAULT_BRANCH = "main"
MANAGED_DELETE_PREFIXES = ("content/publications/", "content/team/")
PUBLISH_LOG_LIMIT = 10


def collect_content_files() -> list[tuple[str, str]]:
	files = []
	settings = frappe.get_single("Site Settings")
	if settings.organization_name:
		files.append(("content/settings/general.md", to_markdown(settings.to_site_frontmatter())))

	home = frappe.get_single("Home Page")
	if home.hero_title:
		files.append(("content/homepage/home.md", to_markdown(home.to_site_frontmatter())))

	privacy = frappe.get_single("Privacy")
	if privacy.last_reviewed:
		files.append(("content/privacy/privacy.md", to_markdown(privacy.to_site_frontmatter())))

	for name in frappe.get_all("Publication", pluck="name"):
		doc = frappe.get_doc("Publication", name)
		files.append((f"content/publications/{doc.slug}.md", to_markdown(doc.to_site_frontmatter())))

	for name in frappe.get_all("Team Member", pluck="name"):
		doc = frappe.get_doc("Team Member", name)
		files.append((f"content/team/{doc.slug}.md", to_markdown(doc.to_site_frontmatter())))

	return files


def content_repo_from_conf() -> ContentRepo:
	token = frappe.conf.get("opero_content_github_token")
	if not token:
		frappe.throw(_("Set opero_content_github_token in site_config.json."))
	repo = frappe.conf.get("opero_content_repo") or DEFAULT_REPO
	base_branch = frappe.conf.get("opero_content_base_branch") or DEFAULT_BRANCH
	return ContentRepo(token=token, repo=repo, base_branch=base_branch)


def planned_content_changes(repo: ContentRepo) -> list[tuple[str, str | None]]:
	planned = collect_content_files()
	if not planned:
		return []
	planned_paths = [path for path, _content in planned]
	existing = repo.existing_files(planned_paths, repo.base_branch)
	files = changed_files(existing, planned)
	files.extend(
		deleted_managed_files(
			planned_paths,
			repo.list_markdown("content/", repo.base_branch),
			MANAGED_DELETE_PREFIXES,
		)
	)
	return files


def pending_entries(files: list[tuple[str, str | None]]) -> list[dict]:
	return [
		{"path": path, "action": "delete" if content is None else "update"}
		for path, content in files
	]


def record_publish(commit_url: str, sha: str, files: list[tuple[str, str | None]]) -> None:
	doc = frappe.get_single("Publisher")
	entries = [
		{
			"published_on": now_datetime(),
			"published_by": frappe.session.user,
			"commit_url": commit_url,
			"sha": sha,
			"file_count": len(files),
			"paths": ", ".join(path for path, _content in files),
		}
	]
	for row in doc.publish_log:
		entries.append(
			{
				"published_on": row.published_on,
				"published_by": row.published_by,
				"commit_url": row.commit_url,
				"sha": row.sha,
				"file_count": row.file_count,
				"paths": row.paths,
			}
		)
	doc.set("publish_log", [])
	for entry in entries[:PUBLISH_LOG_LIMIT]:
		doc.append("publish_log", entry)
	doc.save(ignore_permissions=True)


def _require_publisher() -> None:
	if not frappe.has_permission("Site Settings", "write"):
		frappe.throw(_("Not permitted to publish Opero Site content."))


@frappe.whitelist()
def preview_publish() -> dict:
	_require_publisher()
	planned = collect_content_files()
	if not planned:
		return {
			"files": [],
			"message": _("Nothing to publish. Save content first."),
		}
	try:
		files = planned_content_changes(content_repo_from_conf())
	except GithubError as exc:
		frappe.throw(str(exc))
	if not files:
		return {"files": [], "message": _("Public site content is already up to date.")}
	return {"files": pending_entries(files), "message": None}


@frappe.whitelist()
def publish_to_website() -> dict:
	_require_publisher()
	planned = collect_content_files()
	if not planned:
		return {"commit_url": None, "message": _("Nothing to publish. Save content first.")}

	repo = content_repo_from_conf()
	files = planned_content_changes(repo)
	if not files:
		return {"commit_url": None, "message": _("Public site content is already up to date.")}

	try:
		commit = repo.commit_files(files, message="content: update public site from desk")
	except GithubError as exc:
		frappe.throw(str(exc))
	record_publish(commit["html_url"], commit["sha"], files)
	return {"commit_url": commit["html_url"], "sha": commit["sha"], "files": len(files)}
