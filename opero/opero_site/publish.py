from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

from opero.opero_site.github import ContentRepo, GithubError, changed_files, deleted_managed_files
from opero.opero_site.markdown import preserve_unmanaged_frontmatter, to_markdown
from opero.opero_site.publish_status import (
	PUBLISHED,
	TO_PUBLISH,
	TO_UNPUBLISH,
	UNPUBLISHED,
	is_off_site,
	is_on_site,
	is_to_publish,
	is_to_unpublish,
)

DEFAULT_REPO = "opero-con/opero-content"
DEFAULT_BRANCH = "main"
MANAGED_DELETE_PREFIXES = ("content/publications/", "content/team/")
PUBLISH_LOG_LIMIT = 10
CONTENT_DOCTYPES = ("Publication", "Team Member")
CONTENT_SINGLES = ("Home Page", "Privacy", "Site Settings")


def collect_content_plan() -> tuple[list[tuple[str, str]], list[str]]:
	"""On-site writes plus draft paths that must stay untouched on GitHub.

	Off-site publications are omitted so the next publish deletes them.
	Off-site team members are still written with `active: false`.
	"""
	files = []
	keep = []

	def consider(path: str, doc, ready: bool, *, hide_when_unpublished: bool = False) -> None:
		if not ready:
			return
		if is_on_site(doc) or (hide_when_unpublished and is_off_site(doc)):
			files.append((path, to_markdown(doc.to_site_frontmatter())))
		elif is_off_site(doc):
			return
		else:
			keep.append(path)

	settings = frappe.get_single("Site Settings")
	consider(
		"content/settings/general.md",
		settings,
		bool(settings.organization_name),
	)
	home = frappe.get_single("Home Page")
	consider("content/homepage/home.md", home, bool(home.hero_title))
	privacy = frappe.get_single("Privacy")
	consider("content/privacy/privacy.md", privacy, bool(privacy.last_reviewed))
	for name in frappe.get_all("Publication", pluck="name"):
		doc = frappe.get_doc("Publication", name)
		consider(f"content/publications/{doc.slug}.md", doc, True)
	for name in frappe.get_all("Team Member", pluck="name"):
		doc = frappe.get_doc("Team Member", name)
		consider(f"content/team/{doc.slug}.md", doc, True, hide_when_unpublished=True)
	return files, keep


def collect_content_files() -> list[tuple[str, str]]:
	return collect_content_plan()[0]


def content_repo_from_conf() -> ContentRepo:
	token = frappe.conf.get("opero_content_github_token")
	if not token:
		frappe.throw(_("Set opero_content_github_token in site_config.json."))
	repo = frappe.conf.get("opero_content_repo") or DEFAULT_REPO
	base_branch = frappe.conf.get("opero_content_base_branch") or DEFAULT_BRANCH
	return ContentRepo(token=token, repo=repo, base_branch=base_branch)


def planned_content_changes(repo: ContentRepo, on_progress=None) -> list[tuple[str, str | None]]:
	planned, keep = collect_content_plan()
	write_paths = [path for path, _content in planned]
	existing = (
		repo.existing_files(write_paths, repo.base_branch, on_progress=on_progress) if write_paths else {}
	)
	merged = []
	for path, content in planned:
		current = existing.get(path)
		if current:
			content = preserve_unmanaged_frontmatter(current, content)
		merged.append((path, content))
	files = changed_files(existing, merged)
	files.extend(
		deleted_managed_files(
			write_paths + keep,
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


def settle_publish_statuses() -> None:
	"""After a Publisher run, queued intents become live or off-site states."""
	for doctype in CONTENT_DOCTYPES:
		for name in frappe.get_all(
			doctype,
			filters={"status": ["in", [TO_PUBLISH, TO_UNPUBLISH]]},
			pluck="name",
		):
			_settle_doc(frappe.get_doc(doctype, name))
	for name in CONTENT_SINGLES:
		doc = frappe.get_single(name)
		if is_to_publish(doc) or is_to_unpublish(doc):
			_settle_doc(doc)


def _settle_doc(doc) -> None:
	if is_to_publish(doc):
		doc.db_set("status", PUBLISHED)
		doc.db_set("unpublish", 0, update_modified=False)
	elif is_to_unpublish(doc):
		doc.db_set("status", UNPUBLISHED)
		doc.db_set("unpublish", 1, update_modified=False)


def _require_publisher() -> None:
	if not frappe.has_permission("Site Settings", "write"):
		frappe.throw(_("Not permitted to publish Opero Site content."))


def _emit_progress(done: int, total: int, path: str = "") -> None:
	frappe.publish_realtime(
		"opero_site_progress",
		{"done": done, "total": total, "path": path},
		user=frappe.session.user,
	)


@frappe.whitelist()
def preview_publish() -> dict:
	_require_publisher()
	try:
		files = planned_content_changes(content_repo_from_conf(), on_progress=_emit_progress)
	except GithubError as exc:
		frappe.throw(str(exc))
	if not files:
		return {"files": [], "message": _("Public site content is already up to date.")}
	return {"files": pending_entries(files), "message": None}


@frappe.whitelist()
def publish_to_website() -> dict:
	_require_publisher()
	repo = content_repo_from_conf()
	files = planned_content_changes(repo, on_progress=_emit_progress)
	if not files:
		settle_publish_statuses()
		return {"commit_url": None, "message": _("Public site content is already up to date.")}

	try:
		commit = repo.commit_files(
			files, message="content: update public site from desk", on_progress=_emit_progress
		)
	except GithubError as exc:
		frappe.throw(str(exc))
	record_publish(commit["html_url"], commit["sha"], files)
	settle_publish_statuses()
	return {"commit_url": commit["html_url"], "sha": commit["sha"], "files": len(files)}
