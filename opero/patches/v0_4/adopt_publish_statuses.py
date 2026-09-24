"""Move website statuses to Draft / To publish / To update / Published / To unpublish."""

from __future__ import annotations

import frappe

from opero.opero_site.markdown import parse_frontmatter
from opero.opero_site.publish import CONTENT_DOCTYPES, content_path_for, content_repo_from_conf
from opero.opero_site.publish_status import DRAFT, TO_PUBLISH, TO_UPDATE, publish_status_field

LEGACY_TO_DEPLOY = "To deploy"
LEGACY_UNPUBLISHED = "Unpublished"
ALWAYS_ON_SINGLES = ("Home Page", "Our Work", "Privacy policy", "Site Settings")
EMPLOYEE_STATUS_OPTIONS = "Draft\nTo publish\nTo update\nPublished\nTo unpublish"


def execute():
	update_employee_fields()
	queued = queued_docs()
	live = get_live_paths([path for _doc, path in queued])
	for doc, path in queued:
		status = TO_UPDATE if live is None or path in live else TO_PUBLISH
		doc.db_set(publish_status_field(doc), status, update_modified=False)
	for doctype in CONTENT_DOCTYPES:
		field = publish_status_field(doctype)
		if frappe.db.has_column(doctype, field):
			frappe.db.set_value(doctype, {field: LEGACY_UNPUBLISHED}, field, DRAFT, update_modified=False)
	for name in ALWAYS_ON_SINGLES:
		if frappe.db.get_single_value(name, "status") == LEGACY_TO_DEPLOY:
			frappe.db.set_single_value(name, "status", TO_UPDATE)


def update_employee_fields():
	if frappe.db.exists("Custom Field", "Employee-show_on_website"):
		frappe.db.set_value("Custom Field", "Employee-show_on_website", "label", "Publish")
	if frappe.db.exists("Custom Field", "Employee-website_status"):
		frappe.db.set_value("Custom Field", "Employee-website_status", "options", EMPLOYEE_STATUS_OPTIONS)
	frappe.clear_cache(doctype="Employee")


def queued_docs() -> list[tuple]:
	queued = []
	for doctype in CONTENT_DOCTYPES:
		field = publish_status_field(doctype)
		if not frappe.db.has_column(doctype, field):
			continue
		for name in frappe.get_all(doctype, filters={field: LEGACY_TO_DEPLOY}, pluck="name"):
			doc = frappe.get_doc(doctype, name)
			queued.append((doc, content_path_for(doc)))
	return queued


def get_live_paths(paths: list[str]) -> set[str] | None:
	"""Paths visible on the public site, or None when no GitHub token is set."""
	if not frappe.conf.get("opero_content_github_token"):
		return None
	repo = content_repo_from_conf()
	files = repo.existing_files([path for path in paths if path], repo.base_branch)
	return {path for path, text in files.items() if is_visible(parse_frontmatter(text))}


def is_visible(frontmatter: dict) -> bool:
	return frontmatter.get("active") is not False and frontmatter.get("draft") is not True
