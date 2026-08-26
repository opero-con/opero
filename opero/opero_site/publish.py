from __future__ import annotations

import frappe
from frappe import _

from opero.opero_site.github import ContentRepo, GithubError, changed_files
from opero.opero_site.markdown import to_markdown

DEFAULT_REPO = "opero-con/opero-content"
DEFAULT_BRANCH = "main"


def collect_content_files() -> list[tuple[str, str]]:
	files = []
	settings = frappe.get_single("Site Settings")
	if settings.organization_name:
		files.append(("content/settings/general.md", to_markdown(settings.to_site_frontmatter())))

	home = frappe.get_single("Site Home")
	if home.hero_title:
		files.append(("content/homepage/home.md", to_markdown(home.to_site_frontmatter())))

	privacy = frappe.get_single("Site Privacy")
	if privacy.last_reviewed:
		files.append(("content/privacy/privacy.md", to_markdown(privacy.to_site_frontmatter())))

	for name in frappe.get_all("Site Publication", pluck="name"):
		doc = frappe.get_doc("Site Publication", name)
		files.append((f"content/publications/{doc.slug}.md", to_markdown(doc.to_site_frontmatter())))

	for name in frappe.get_all("Site Team Member", pluck="name"):
		doc = frappe.get_doc("Site Team Member", name)
		files.append((f"content/team/{doc.slug}.md", to_markdown(doc.to_site_frontmatter())))

	return files


def content_repo_from_conf() -> ContentRepo:
	token = frappe.conf.get("opero_content_github_token")
	if not token:
		frappe.throw(_("Set opero_content_github_token in site_config.json."))
	repo = frappe.conf.get("opero_content_repo") or DEFAULT_REPO
	base_branch = frappe.conf.get("opero_content_base_branch") or DEFAULT_BRANCH
	return ContentRepo(token=token, repo=repo, base_branch=base_branch)


@frappe.whitelist()
def publish_to_website() -> dict:
	if not frappe.has_permission("Site Settings", "write"):
		frappe.throw(_("Not permitted to publish website content."))

	planned = collect_content_files()
	if not planned:
		return {"commit_url": None, "message": _("Nothing to publish. Save website content first.")}

	repo = content_repo_from_conf()
	existing = repo.existing_files([path for path, _content in planned], repo.base_branch)
	files = changed_files(existing, planned)
	if not files:
		return {"commit_url": None, "message": _("Public site content is already up to date.")}

	try:
		commit = repo.commit_files(files, message="content: update public site from desk")
	except GithubError as exc:
		frappe.throw(str(exc))
	return {"commit_url": commit["html_url"], "sha": commit["sha"], "files": len(files)}
