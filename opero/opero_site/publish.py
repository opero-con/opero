from __future__ import annotations

import difflib
from urllib.parse import unquote

import frappe
from frappe import _
from frappe.utils import escape_html, now_datetime

from opero.opero.doctype.enterprise.enterprise import enterprise_content_slug
from opero.opero_site.cover_focal_point import fill_missing_cover_framing
from opero.opero_site.doctype.partner.partner import partner_content_slug
from opero.opero_site.github import ContentRepo, GithubError, changed_files, deleted_managed_files
from opero.opero_site.markdown import media_references, preserve_unmanaged_frontmatter, to_markdown
from opero.opero_site.media import export_planned_media, git_blob_sha
from opero.opero_site.publish_status import (
	ALWAYS_ON_SITE,
	DRAFT,
	PUBLISHED,
	QUEUED,
	TO_UNPUBLISH,
	is_on_site,
	is_queued,
	is_to_unpublish,
	publish_status_field,
)

DEFAULT_REPO = "opero-con/opero-content"
DEFAULT_BRANCH = "main"
MANAGED_DELETE_PREFIXES = (
	"content/publications/",
	"content/team/",
	"content/enterprises/",
	"content/partners/",
)
MEDIA_DELETE_PREFIXES = ("media/publications/", "media/team/", "media/enterprises/", "media/partners/")
DEPLOY_LOG_LIMIT = 10
DEPLOY_LOG_FIELDS = (
	"deployed_on",
	"deployed_by",
	"commit_url",
	"sha",
	"file_count",
	"paths",
	"website_status",
	"build_url",
)
CONTENT_DOCTYPES = ("Publication", "Employee", "Enterprise", "Partner")
CONTENT_SINGLES = ("Home Page", "Privacy policy", "Site Settings")
SITE_CONTENT_DOCTYPES = CONTENT_DOCTYPES + CONTENT_SINGLES
PENDING_EVENT = "opero_site_pending"
PENDING_CACHE_KEY = "opero_site_pending_rows"

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
	if doc.doctype == "Partner":
		slug = partner_content_slug(getattr(doc, "partner_name", None) or "")
		return f"content/partners/{slug}.md" if slug else None
	slug = getattr(doc, "slug", None)
	if not slug:
		return None
	if doc.doctype == "Publication":
		return f"content/publications/{slug}.md"
	if doc.doctype == "Employee":
		return f"content/team/{slug}.md"
	return None


_FIXED_PATH_LABELS = {path: (doctype, "Site pages") for doctype, path in CONTENT_PATHS.items()}
_CONTENT_PATH_GROUPS = (
	("content/publications/", "Publication", "Publications"),
	("content/team/", "Employee", "Team"),
	("content/enterprises/", "Enterprise", "Enterprises"),
	("content/partners/", "Partner", "Partners"),
)


def _slug_from_path(path: str) -> str:
	return path.rsplit("/", 1)[-1].removesuffix(".md")


def _prettify_slug(slug: str) -> str:
	return slug.replace("-", " ").replace("_", " ").strip().title()


def _live_enterprise(slug: str) -> tuple[str, str] | None:
	for row in frappe.get_all("Enterprise", fields=["name", "enterprise_name"]):
		if enterprise_content_slug(row.enterprise_name) == slug:
			return row.enterprise_name, row.name
	return None


def _live_partner(slug: str) -> tuple[str, str] | None:
	for row in frappe.get_all("Partner", fields=["name", "partner_name"]):
		if partner_content_slug(row.partner_name) == slug:
			return row.partner_name, row.name
	return None


def _live_publication(slug: str) -> tuple[str, str] | None:
	row = frappe.db.get_value("Publication", {"slug": slug}, ["title", "name"], as_dict=True)
	return (row.title, row.name) if row else None


def _live_employee(slug: str) -> tuple[str, str] | None:
	row = frappe.db.get_value("Employee", {"slug": slug}, ["employee_name", "name"], as_dict=True)
	return (row.employee_name, row.name) if row else None


def content_label_for(path: str) -> dict:
	"""Human title, content-type group, and (when the doc still exists) its route."""
	fixed = _FIXED_PATH_LABELS.get(path)
	if fixed:
		doctype, group = fixed
		return {"title": doctype, "group": group, "doctype": doctype, "docname": None, "is_single": True}

	for prefix, doctype, group in _CONTENT_PATH_GROUPS:
		if not path.startswith(prefix):
			continue
		slug = _slug_from_path(path)
		if doctype == "Enterprise":
			found = _live_enterprise(slug)
			title, docname = found if found else (None, None)
		elif doctype == "Employee":
			found = _live_employee(slug)
			title, docname = found if found else (None, None)
		elif doctype == "Partner":
			found = _live_partner(slug)
			title, docname = found if found else (None, None)
		else:
			found = _live_publication(slug)
			title, docname = found if found else (None, None)
		return {
			"title": title or _prettify_slug(slug),
			"group": group,
			"doctype": doctype if docname else None,
			"docname": docname,
			"is_single": False,
		}

	return {
		"title": _prettify_slug(_slug_from_path(path)),
		"group": "Other",
		"doctype": None,
		"docname": None,
		"is_single": False,
	}


def _enrich_pending(rows: list[dict]) -> list[dict]:
	return [{**row, **content_label_for(row["path"])} for row in rows]


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
		rename = {"path": old_path, "action": "delete", "source": [doc.doctype, doc.name]}
		if (
			renamed
			and doc.doctype == "Publication"
			and (is_on_site(previous) or is_to_unpublish(previous) or is_on_site(doc) or is_to_unpublish(doc))
		):
			entries.append(rename)
		elif (
			renamed
			and doc.doctype in ("Employee", "Enterprise", "Partner")
			and (is_on_site(previous) or is_to_unpublish(previous))
		):
			entries.append(rename)

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
		elif is_to_unpublish(doc):
			entries.append({"path": path, "action": "delete"})
		return _unique_pending(entries)

	if doc.doctype in ("Employee", "Enterprise", "Partner"):
		if is_on_site(doc) or is_to_unpublish(doc):
			entries.append({"path": path, "action": "update"})
		return _unique_pending(entries)

	return _unique_pending(entries)


def _unique_pending(entries: list[dict]) -> list[dict]:
	return list({row["path"]: row for row in entries}.values())


def _pending_row(row: dict) -> dict:
	"""Cached pending row: its action, plus the record a rename's old file belongs to."""
	cached = {"path": row["path"], "action": row["action"]}
	if row.get("source"):
		cached["source"] = list(row["source"])
	return cached


def _pending_cache() -> dict[str, dict]:
	return dict(frappe.cache.get_value(PENDING_CACHE_KEY) or {})


def _set_pending_cache(by_path: dict[str, dict]) -> None:
	frappe.cache.set_value(PENDING_CACHE_KEY, by_path)


def merge_pending_cache(files: list[dict]) -> list[dict]:
	by_path = _pending_cache()
	for row in files:
		by_path[row["path"]] = _pending_row(row)
	_set_pending_cache(by_path)
	return [by_path[path] for path in sorted(by_path)]


def replace_pending_cache(files: list[dict]) -> None:
	"""Replace the pending list with a GitHub compare, keeping known rename owners."""
	previous = _pending_cache()
	by_path = {}
	for row in files:
		source = row.get("source") or previous.get(row["path"], {}).get("source")
		by_path[row["path"]] = _pending_row({**row, "source": source})
	_set_pending_cache(by_path)


def clear_pending_cache() -> None:
	frappe.cache.delete_value(PENDING_CACHE_KEY)


def drop_pending_path(path: str) -> None:
	drop_pending_paths([path])


def drop_pending_paths(paths: list[str]) -> None:
	by_path = _pending_cache()
	if any([by_path.pop(path, None) for path in paths]):
		_set_pending_cache(by_path)


def pending_from_status() -> list[dict]:
	"""Queued publish intents that should appear even before a GitHub compare."""
	entries: list[dict] = []
	for doctype in CONTENT_DOCTYPES:
		status_field = publish_status_field(doctype)
		if doctype == "Enterprise":
			fields = [status_field, "enterprise_name"]
		elif doctype == "Partner":
			fields = [status_field, "partner_name"]
		else:
			fields = [status_field, "slug"]
		for row in frappe.get_all(
			doctype,
			filters={status_field: ["in", QUEUED]},
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
		if is_queued(doc) and _doc_is_ready(doc):
			path = content_path_for(doc)
			if path:
				entries.append({"path": path, "action": "update"})
	return _unique_pending(entries)


def desk_pending_entries() -> list[dict]:
	by_path = {row["path"]: row for row in pending_from_status()}
	by_path.update(_pending_cache())
	return _enrich_pending([by_path[path] for path in sorted(by_path)])


def selection_paths(paths: list[str]) -> list[str]:
	"""Selected content files plus the other half of any rename they belong to."""
	selected = list(dict.fromkeys(paths))
	for path in selected:
		if not path.startswith("content/") or not path.endswith(".md"):
			frappe.throw(_("{0} is not a website content file.").format(path))
	for old_path, row in sorted(_pending_cache().items()):
		source = row.get("source")
		if not source or not frappe.db.exists(*source):
			continue
		pair = [old_path, content_path_for(frappe.get_doc(*source))]
		if set(pair) & set(selected):
			selected.extend(path for path in pair if path and path not in selected)
	return selected


def document_deploy_paths(doc) -> list[str]:
	"""This record's content file plus any old file a rename left on the website."""
	path = content_path_for(doc)
	return selection_paths([path]) if path else []


def documents_for_paths(paths: list[str]) -> list:
	"""Desk records behind content paths, including the owner of a rename's old file."""
	cache = _pending_cache()
	refs = []
	for path in paths:
		label = content_label_for(path)
		if label["is_single"]:
			refs.append((label["doctype"], label["doctype"]))
		elif label["docname"]:
			refs.append((label["doctype"], label["docname"]))
		source = cache.get(path, {}).get("source")
		if source and frappe.db.exists(*source):
			refs.append(tuple(source))
	return [frappe.get_doc(*ref) for ref in dict.fromkeys(refs)]


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
		{"files": _enrich_pending(files)},
		user=frappe.session.user,
		after_commit=True,
	)


def collect_content_plan() -> tuple[list[tuple[str, str]], list[str]]:
	"""On-site writes plus draft paths that must stay untouched on GitHub.

	Publications to unpublish are omitted so a deploy that selects them deletes them.
	Team members, enterprises, and partners to unpublish are written with `active: false`.
	"""
	files = []
	keep = []

	def consider(path: str, doc, ready: bool, *, hide_when_unpublished: bool = False) -> None:
		if not ready:
			return
		if is_on_site(doc) or (hide_when_unpublished and is_to_unpublish(doc)):
			files.append((path, to_markdown(doc.to_site_frontmatter())))
		elif is_to_unpublish(doc):
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
	for name in frappe.get_all("Employee", pluck="name", filters={"slug": ["is", "set"]}):
		doc = frappe.get_doc("Employee", name)
		consider(f"content/team/{doc.slug}.md", doc, True, hide_when_unpublished=True)
	for name in frappe.get_all("Enterprise", pluck="name"):
		doc = frappe.get_doc("Enterprise", name)
		path = content_path_for(doc)
		if not path:
			continue
		consider(path, doc, True, hide_when_unpublished=True)
	for name in frappe.get_all("Partner", pluck="name"):
		doc = frappe.get_doc("Partner", name)
		path = content_path_for(doc)
		if path:
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


def planned_content_changes(
	repo: ContentRepo, on_progress=None, paths: list[str] | None = None
) -> list[tuple[str, str | bytes | None]]:
	"""GitHub changes that make the website match Desk, limited to `paths` when given.

	Pending changes outside `paths` keep their current GitHub version.
	"""
	fill_missing_cover_framing(repo)
	planned, keep = collect_content_plan()
	selected = None if paths is None else set(paths)
	if selected is not None:
		keep = keep + [path for path, _content in planned if path not in selected]
		planned = [(path, content) for path, content in planned if path in selected]
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
	deletes = deleted_managed_files(
		write_paths + keep,
		repo.list_markdown("content/", repo.base_branch),
		MANAGED_DELETE_PREFIXES,
	)
	if selected is not None:
		keep = keep + [path for path, _content in deletes if path not in selected]
		deletes = [(path, content) for path, content in deletes if path in selected]
	files.extend(deletes)
	blobs = repo.tree_blobs(repo.base_branch)
	media_paths = [path for path, _content in media]
	for path, content in media:
		if blobs.get(path) != git_blob_sha(content):
			files.append((path, content))

	remaining = list(merged)
	if keep:
		remaining.extend(repo.existing_files(keep, repo.base_branch).items())
	references = {path: media_references(content) for path, content in remaining}
	require_media_present(references, set(blobs) | set(media_paths))

	# A media file is still wanted if it was freshly re-exported this pass,
	# OR if any content file that will remain in the repo after this deploy
	# still references it. Without the latter, any doc whose media field
	# survived load_from_website() as a plain /media/... string (the normal
	# state for publications and team members, and the fallback for
	# enterprises whenever the logo re-download fails) looks orphaned and
	# gets pruned on the very next publish, even though nothing changed.
	referenced_media = set(media_paths).union(*references.values())
	prunable = list(blobs) if selected is None else selected_media(repo, selected, blobs)
	files.extend(deleted_managed_files(list(referenced_media), prunable, MEDIA_DELETE_PREFIXES))
	return files


def selected_media(repo: ContentRepo, selected: set[str], blobs: dict[str, str]) -> list[str]:
	"""Media the selected files use on GitHub now; only these may be pruned by a selective deploy."""
	current = repo.existing_files(sorted(selected), repo.base_branch)
	used = {unquote(reference) for content in current.values() for reference in media_references(content)}
	return [path for path in blobs if path in used]


def require_media_present(references: dict[str, set[str]], available: set[str]) -> None:
	"""Refuse a deploy the website build would reject for a missing `/media/...` file."""
	missing = [
		_("{0} uses {1}").format(content_label_for(path)["title"], reference)
		for path, paths in sorted(references.items())
		for reference in sorted(paths)
		if unquote(reference) not in available
	]
	if missing:
		frappe.throw(
			_("The website would fail to build because these media files are not in the content repository:")
			+ "<br>"
			+ "<br>".join(escape_html(line) for line in missing),
			title=_("Missing media"),
		)


def pending_entries(files: list[tuple[str, str | None]]) -> list[dict]:
	rows = [{"path": path, "action": "delete" if content is None else "update"} for path, content in files]
	return _enrich_pending(rows)


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
			"website_status": "Building",
		}
	]
	entries.extend({field: row.get(field) for field in DEPLOY_LOG_FIELDS} for row in doc.deploy_log)
	doc.set("deploy_log", [])
	for entry in entries[:DEPLOY_LOG_LIMIT]:
		doc.append("deploy_log", entry)
	doc.save(ignore_permissions=True)


def settle_publish_statuses() -> None:
	"""After a deploy, queued records become Published, or Draft once taken down."""
	for doctype in CONTENT_DOCTYPES:
		status_field = publish_status_field(doctype)
		for name in frappe.get_all(
			doctype,
			filters={status_field: ["in", QUEUED]},
			pluck="name",
		):
			_settle_doc(frappe.get_doc(doctype, name))
	for name in CONTENT_SINGLES:
		doc = frappe.get_single(name)
		if doc.status != PUBLISHED:
			_settle_doc(doc)


def settle_documents(docs: list) -> None:
	for doc in docs:
		if is_queued(doc):
			_settle_doc(doc)


def _settle_doc(doc) -> None:
	field = publish_status_field(doc)
	if doc.doctype in ALWAYS_ON_SITE:
		doc.db_set(field, PUBLISHED)
		return
	doc.db_set(field, DRAFT if is_to_unpublish(doc) else PUBLISHED)


def _require_deploy_permission() -> None:
	if not frappe.has_permission("Site Settings", "write"):
		frappe.throw(_("Not permitted to deploy Opero Site content."))


def _require_document_deploy_permission(doc) -> None:
	if frappe.has_permission("Site Settings", "write"):
		return
	if doc.doctype == "Publication" and "Website Publication Publisher" in frappe.get_roles():
		doc.check_permission("write")
		return
	frappe.throw(_("Not permitted to deploy this website record."), frappe.PermissionError)


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


def commit_planned_changes(repo: ContentRepo, paths: list[str], message: str = "") -> dict:
	files = planned_content_changes(repo, on_progress=_emit_progress, paths=paths)
	if not files:
		return {"commit_url": None, "message": _("Public site content is already up to date.")}
	try:
		commit = repo.commit_files(
			files, message=message or "content: update public site from desk", on_progress=_emit_progress
		)
	except GithubError as exc:
		frappe.throw(str(exc))
	record_deploy(commit["html_url"], commit["sha"], files)
	return {"commit_url": commit["html_url"], "sha": commit["sha"], "files": len(files)}


def deploy_paths(paths: list[str], message: str = "") -> dict:
	"""Deploy only these content files; every other pending change stays queued."""
	docs = documents_for_paths(paths)
	result = commit_planned_changes(content_repo_from_conf(), paths, message)
	settle_documents(docs)
	drop_pending_paths(paths)
	return result


def preview_paths(paths: list[str]) -> dict:
	try:
		files = planned_content_changes(content_repo_from_conf(), on_progress=_emit_progress, paths=paths)
	except GithubError as exc:
		frappe.throw(str(exc))
	return {"paths": paths, "files": pending_entries(files)}


def get_selected_paths(paths) -> list[str]:
	selected = frappe.parse_json(paths) if isinstance(paths, str) else paths
	if not selected:
		frappe.throw(_("Select the changes to deploy."))
	return selection_paths(selected)


@frappe.whitelist()
def preview_selected_deploy(paths) -> dict:
	"""What deploying only the selected Deploy Center rows would change on the website."""
	_require_deploy_permission()
	return preview_paths(get_selected_paths(paths))


@frappe.whitelist()
def deploy_selected(paths) -> dict:
	"""Deploy the selected Deploy Center rows alone; other pending changes stay queued."""
	_require_deploy_permission()
	return deploy_paths(get_selected_paths(paths))


def get_site_document(doctype: str, name: str):
	if doctype not in SITE_CONTENT_DOCTYPES:
		frappe.throw(_("{0} is not website content.").format(doctype))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	return doc


@frappe.whitelist()
def preview_document_deploy(doctype: str, name: str) -> dict:
	"""What deploying only this record would change on the website."""
	doc = get_site_document(doctype, name)
	_require_document_deploy_permission(doc)
	return preview_paths(document_deploy_paths(doc))


@frappe.whitelist()
def deploy_document(doctype: str, name: str) -> dict:
	"""Deploy this record alone; other pending changes stay queued."""
	doc = get_site_document(doctype, name)
	_require_document_deploy_permission(doc)
	return deploy_paths(document_deploy_paths(doc), message=f"content: update {doctype} {name} from desk")


def content_diff(repo: ContentRepo, path: str) -> dict:
	"""What one pending file will look like on the site, compared with what's live now."""
	files = planned_content_changes(repo)
	label = content_label_for(path)
	match = next(((p, content) for p, content in files if p == path), None)
	if not match:
		return {
			"path": path,
			**label,
			"diff": [],
			"message": _("Nothing pending for {0}.").format(label["title"]),
		}

	_path, planned_content = match
	if planned_content is not None and not isinstance(planned_content, str):
		return {"path": path, **label, "is_binary": True, "diff": []}

	existing = repo.existing_files([path], repo.base_branch).get(path)
	if planned_content is None:
		return {"path": path, **label, "is_delete": True, "diff": (existing or "").splitlines()}
	if existing is None:
		return {"path": path, **label, "is_new": True, "diff": planned_content.splitlines()}

	diff = list(
		difflib.unified_diff(
			existing.splitlines(),
			planned_content.splitlines(),
			fromfile="published",
			tofile="pending",
			lineterm="",
		)
	)
	return {"path": path, **label, "diff": diff}


@frappe.whitelist()
def preview_content_diff(path: str) -> dict:
	_require_deploy_permission()
	try:
		return content_diff(content_repo_from_conf(), path)
	except GithubError as exc:
		frappe.throw(str(exc))
