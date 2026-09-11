from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.utils import now_datetime

from opero.opero.doctype.enterprise.enterprise import enterprise_content_slug
from opero.opero_site.github import ContentRepo, GithubError, changed_files, deleted_managed_files
from opero.opero_site.markdown import preserve_unmanaged_frontmatter, to_markdown
from opero.opero_site.media import export_planned_media, git_blob_sha
from opero.opero_site.publish_status import (
	ALWAYS_ON_SITE,
	PUBLISHED,
	TO_DEPLOY,
	TO_UNPUBLISH,
	UNPUBLISHED,
	is_off_site,
	is_on_site,
	is_to_deploy,
	is_to_unpublish,
	publish_status_field,
)

DEFAULT_REPO = "opero-con/opero-content"
DEFAULT_BRANCH = "main"
MANAGED_DELETE_PREFIXES = ("content/publications/", "content/team/", "content/enterprises/")
MEDIA_DELETE_PREFIXES = ("media/publications/", "media/team/", "media/enterprises/")
DEPLOY_LOG_LIMIT = 10
CONTENT_DOCTYPES = ("Publication", "Team Member", "Enterprise")
CONTENT_SINGLES = ("Home Page", "Privacy policy", "Site Settings")
SITE_CONTENT_DOCTYPES = CONTENT_DOCTYPES + CONTENT_SINGLES
PENDING_EVENT = "opero_site_pending"
PENDING_CACHE_KEY = "opero_site_pending_files"

CONTENT_PATHS = {
	"Site Settings": "content/settings/general.md",
	"Home Page": "content/homepage/home.md",
	"Privacy policy": "content/privacy/privacy.md",
}


def content_path_for(doc) -> str | None:
	fixed = CONTENT_PATHS.get(doc.doctype)
	if fixed:
		return fixed
	if doc.doctype == "Enterprise":
		slug = enterprise_content_slug(getattr(doc, "enterprise_name", None) or "")
		return f"content/enterprises/{slug}.md" if slug else None
	slug = getattr(doc, "slug", None)
	if not slug:
		return None
	if doc.doctype == "Publication":
		return f"content/publications/{slug}.md"
	if doc.doctype == "Team Member":
		return f"content/team/{slug}.md"
	return None


def _doc_is_ready(doc) -> bool:
	if doc.doctype == "Site Settings":
		return bool(doc.organization_name)
	if doc.doctype == "Home Page":
		return bool(frappe.get_single("Hero").hero_title)
	if doc.doctype == "Privacy policy":
		return bool(doc.last_reviewed)
	return True


def pending_push_for_doc(doc, *, deleted: bool = False) -> list[dict]:
	"""Desk-side pending rows for one content save (no GitHub round-trip)."""
	entries: list[dict] = []
	previous = None if deleted or doc.is_new() else doc.get_doc_before_save()
	if previous:
		old_path = content_path_for(previous)
		new_path = content_path_for(doc)
		renamed = bool(old_path and new_path and old_path != new_path)
		if renamed and doc.doctype == "Publication" and (
			is_on_site(previous) or is_off_site(previous) or is_on_site(doc) or is_off_site(doc)
		):
			entries.append({"path": old_path, "action": "delete"})
		elif renamed and doc.doctype in ("Team Member", "Enterprise") and (
			is_on_site(previous) or is_off_site(previous)
		):
			entries.append({"path": old_path, "action": "delete"})

	path = content_path_for(doc)
	if not path:
		return entries

	if deleted:
		if doc.doctype in CONTENT_DOCTYPES:
			entries.append({"path": path, "action": "delete"})
		return _unique_pending(entries)

	if doc.doctype in ALWAYS_ON_SITE:
		if _doc_is_ready(doc):
			entries.append({"path": path, "action": "update"})
		return _unique_pending(entries)

	if doc.doctype == "Publication":
		if is_on_site(doc):
			entries.append({"path": path, "action": "update"})
		elif is_off_site(doc):
			entries.append({"path": path, "action": "delete"})
		return _unique_pending(entries)

	if doc.doctype in ("Team Member", "Enterprise"):
		if is_on_site(doc) or is_off_site(doc):
			entries.append({"path": path, "action": "update"})
		return _unique_pending(entries)

	return _unique_pending(entries)


def _unique_pending(entries: list[dict]) -> list[dict]:
	by_path: dict[str, str] = {}
	for row in entries:
		by_path[row["path"]] = row["action"]
	return [{"path": path, "action": action} for path, action in by_path.items()]


def _pending_cache() -> dict[str, str]:
	return dict(frappe.cache.get_value(PENDING_CACHE_KEY) or {})


def _set_pending_cache(by_path: dict[str, str]) -> None:
	frappe.cache.set_value(PENDING_CACHE_KEY, by_path)


def merge_pending_cache(files: list[dict]) -> list[dict]:
	by_path = _pending_cache()
	for row in files:
		by_path[row["path"]] = row["action"]
	_set_pending_cache(by_path)
	return [{"path": path, "action": action} for path, action in sorted(by_path.items())]


def replace_pending_cache(files: list[dict]) -> None:
	_set_pending_cache({row["path"]: row["action"] for row in files})


def clear_pending_cache() -> None:
	frappe.cache.delete_value(PENDING_CACHE_KEY)


def pending_from_status() -> list[dict]:
	"""Queued publish intents that should appear even before a GitHub compare."""
	entries: list[dict] = []
	for doctype in CONTENT_DOCTYPES:
		status_field = publish_status_field(doctype)
		fields = [status_field, "enterprise_name"] if doctype == "Enterprise" else [status_field, "slug"]
		for row in frappe.get_all(
			doctype,
			filters={status_field: ["in", [TO_DEPLOY, TO_UNPUBLISH]]},
			fields=fields,
		):
			path = content_path_for(frappe._dict(doctype=doctype, **row))
			if not path:
				continue
			row_status = row.get(status_field)
			if doctype == "Publication" and row_status == TO_UNPUBLISH:
				entries.append({"path": path, "action": "delete"})
			else:
				entries.append({"path": path, "action": "update"})
	for name in CONTENT_SINGLES:
		doc = frappe.get_single(name)
		if is_to_deploy(doc) and _doc_is_ready(doc):
			path = content_path_for(doc)
			if path:
				entries.append({"path": path, "action": "update"})
	return _unique_pending(entries)


def desk_pending_entries() -> list[dict]:
	by_path = {row["path"]: row["action"] for row in pending_from_status()}
	by_path.update(_pending_cache())
	return [{"path": path, "action": action} for path, action in sorted(by_path.items())]


def queue_home_page_deploy(doc=None, method: str | None = None) -> None:
	"""A Home Page section save queues the combined homepage for deploy."""
	if frappe.flags.get("opero_site_syncing"):
		return
	frappe.get_single("Home Page").save(ignore_permissions=True)


def notify_pending_website_changes(doc, method: str | None = None) -> None:
	"""Push this save into the Deploy Center pending list (cache + realtime)."""
	if frappe.flags.get("opero_site_syncing"):
		return
	if doc.doctype not in SITE_CONTENT_DOCTYPES:
		return
	files = pending_push_for_doc(doc, deleted=method == "on_trash")
	if not files:
		return
	merge_pending_cache(files)
	frappe.publish_realtime(
		PENDING_EVENT,
		{"files": files},
		user=frappe.session.user,
		after_commit=True,
	)


def collect_content_plan() -> tuple[list[tuple[str, str]], list[str]]:
	"""On-site writes plus draft paths that must stay untouched on GitHub.

	Off-site publications are omitted so the next deploy deletes them.
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
	consider("content/homepage/home.md", home, _doc_is_ready(home))
	privacy = frappe.get_single("Privacy policy")
	consider("content/privacy/privacy.md", privacy, bool(privacy.last_reviewed))
	for name in frappe.get_all("Publication", pluck="name"):
		doc = frappe.get_doc("Publication", name)
		consider(f"content/publications/{doc.slug}.md", doc, True)
	for name in frappe.get_all("Team Member", pluck="name"):
		doc = frappe.get_doc("Team Member", name)
		consider(f"content/team/{doc.slug}.md", doc, True, hide_when_unpublished=True)
	for name in frappe.get_all("Enterprise", pluck="name"):
		doc = frappe.get_doc("Enterprise", name)
		path = content_path_for(doc)
		if not path:
			continue
		consider(path, doc, True, hide_when_unpublished=True)
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


# Frontmatter is plain YAML scalars, which may contain unescaped spaces
# (e.g. "cover: /media/publications/Workshop 2 - 8 (1).jpg"), so a
# reference runs to end of line, not to the first whitespace.
_MEDIA_REFERENCE_PATTERN = re.compile(r"/media/[^\r\n]+")


def _media_refs_in_text(text: str) -> set[str]:
	refs = set()
	for match in _MEDIA_REFERENCE_PATTERN.findall(text):
		refs.add(match.strip().strip("\"'").lstrip("/"))
	return refs


def planned_content_changes(repo: ContentRepo, on_progress=None) -> list[tuple[str, str | bytes | None]]:
	planned, keep = collect_content_plan()
	planned, media = export_planned_media(planned)
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
	blobs = repo.tree_blobs(repo.base_branch)
	media_paths = [path for path, _content in media]
	for path, content in media:
		if blobs.get(path) != git_blob_sha(content):
			files.append((path, content))

	# A media file is still wanted if it was freshly re-exported this pass,
	# OR if any content file that will remain in the repo after this deploy
	# still references it. Without the latter, any doc whose media field
	# survived load_from_website() as a plain /media/... string (the normal
	# state for publications and team members, and the fallback for
	# enterprises whenever the logo re-download fails) looks orphaned and
	# gets pruned on the very next publish, even though nothing changed.
	referenced_media = set(media_paths)
	for _path, content in merged:
		referenced_media.update(_media_refs_in_text(content))
	if keep:
		for content in repo.existing_files(keep, repo.base_branch).values():
			referenced_media.update(_media_refs_in_text(content))

	files.extend(deleted_managed_files(list(referenced_media), list(blobs), MEDIA_DELETE_PREFIXES))
	return files


def pending_entries(files: list[tuple[str, str | None]]) -> list[dict]:
	return [
		{"path": path, "action": "delete" if content is None else "update"}
		for path, content in files
	]


def record_deploy(commit_url: str, sha: str, files: list[tuple[str, str | None]]) -> None:
	doc = frappe.get_single("Deploy Center")
	entries = [
		{
			"deployed_on": now_datetime(),
			"deployed_by": frappe.session.user,
			"commit_url": commit_url,
			"sha": sha,
			"file_count": len(files),
			"paths": ", ".join(path for path, _content in files),
		}
	]
	for row in doc.deploy_log:
		entries.append(
			{
				"deployed_on": row.deployed_on,
				"deployed_by": row.deployed_by,
				"commit_url": row.commit_url,
				"sha": row.sha,
				"file_count": row.file_count,
				"paths": row.paths,
			}
		)
	doc.set("deploy_log", [])
	for entry in entries[:DEPLOY_LOG_LIMIT]:
		doc.append("deploy_log", entry)
	doc.save(ignore_permissions=True)


def settle_publish_statuses() -> None:
	"""After a deploy, queued intents become live or off-site states."""
	for doctype in CONTENT_DOCTYPES:
		status_field = publish_status_field(doctype)
		for name in frappe.get_all(
			doctype,
			filters={status_field: ["in", [TO_DEPLOY, TO_UNPUBLISH]]},
			pluck="name",
		):
			_settle_doc(frappe.get_doc(doctype, name))
	for name in CONTENT_SINGLES:
		doc = frappe.get_single(name)
		if doc.status != PUBLISHED:
			_settle_doc(doc)


def _settle_doc(doc) -> None:
	field = publish_status_field(doc)
	if doc.doctype in ALWAYS_ON_SITE:
		doc.db_set(field, PUBLISHED)
		return
	if is_to_deploy(doc):
		doc.db_set(field, PUBLISHED)
	elif is_to_unpublish(doc):
		doc.db_set(field, UNPUBLISHED)


def _require_deploy_permission() -> None:
	if not frappe.has_permission("Site Settings", "write"):
		frappe.throw(_("Not permitted to deploy Opero Site content."))


def _emit_progress(done: int, total: int, path: str = "") -> None:
	frappe.publish_realtime(
		"opero_site_progress",
		{"done": done, "total": total, "path": path},
		user=frappe.session.user,
	)


@frappe.whitelist()
def preview_pending() -> dict:
	"""Fast pending list from Desk saves and publish status (no GitHub)."""
	_require_deploy_permission()
	files = desk_pending_entries()
	if not files:
		return {"files": [], "message": _("Nothing due.")}
	return {"files": files, "message": None}


@frappe.whitelist()
def preview_deploy() -> dict:
	_require_deploy_permission()
	try:
		files = planned_content_changes(content_repo_from_conf(), on_progress=_emit_progress)
	except GithubError as exc:
		frappe.throw(str(exc))
	rows = pending_entries(files)
	replace_pending_cache(rows)
	if not rows:
		return {"files": [], "message": _("Public site content is already up to date.")}
	return {"files": rows, "message": None}


@frappe.whitelist()
def deploy_to_website() -> dict:
	_require_deploy_permission()
	repo = content_repo_from_conf()
	files = planned_content_changes(repo, on_progress=_emit_progress)
	if not files:
		settle_publish_statuses()
		clear_pending_cache()
		return {"commit_url": None, "message": _("Public site content is already up to date.")}

	try:
		commit = repo.commit_files(
			files, message="content: update public site from desk", on_progress=_emit_progress
		)
	except GithubError as exc:
		frappe.throw(str(exc))
	record_deploy(commit["html_url"], commit["sha"], files)
	settle_publish_statuses()
	clear_pending_cache()
	return {"commit_url": commit["html_url"], "sha": commit["sha"], "files": len(files)}
