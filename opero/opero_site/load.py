from __future__ import annotations

import os

import frappe
from frappe import _
from frappe.utils import cint, cstr, getdate
from frappe.utils.file_manager import save_file

from opero.opero_site.body_html import body_sections_to_html, paragraphs_to_html
from opero.opero_site.github import ContentRepo, GithubError
from opero.opero_site.markdown import parse_frontmatter, same_managed_content, to_markdown
from opero.opero_site.publish import clear_pending_cache, content_repo_from_conf
from opero.opero_site.publish_status import DRAFT, PUBLISHED, UNPUBLISHED
from opero.opero_site.utils import (
	hero_image_focus_label,
	normalize_publication_type,
	parse_hero_carousel_item,
)


def slug_from_path(path: str) -> str:
	return path.rsplit("/", 1)[-1].removesuffix(".md")


def _text(value) -> str:
	return cstr(value).strip()


def _join_lines(value) -> str:
	if isinstance(value, list):
		return "\n".join(_text(item) for item in value if _text(item))
	return _text(value)


def apply_settings(doc, data: dict):
	seo = data.get("seo") or {}
	doc.organization_name = _text(data.get("organizationName"))
	doc.email = _text(data.get("email"))
	doc.communications_email = _text(data.get("communicationsEmail"))
	doc.phone = _text(data.get("phone"))
	doc.training_phone = _text(data.get("trainingPhone"))
	doc.linkedin_url = _text(data.get("linkedinUrl"))
	doc.twitter_url = _text(data.get("twitterUrl"))
	doc.seo_title = _text(seo.get("title"))
	doc.seo_description = _text(seo.get("description"))
	doc.canonical_url = _text(seo.get("canonicalUrl"))
	doc.og_image = _text(seo.get("ogImage"))
	doc.status = PUBLISHED
	doc.set("offices", [])
	for office in data.get("offices") or []:
		doc.append(
			"offices",
			{
				"office_label": _text(office.get("label")),
				"building": _text(office.get("building")),
				"street": _text(office.get("street")),
				"city": _text(office.get("city")),
				"country": _text(office.get("country")),
			},
		)


def apply_home_hero(doc, data: dict):
	hero = data.get("hero") or {}
	doc.hero_eyebrow = _text(hero.get("eyebrow"))
	doc.hero_title = _text(hero.get("title"))
	doc.hero_description = _text(hero.get("description"))
	doc.set("hero_images", [])
	primary = _text(hero.get("image"))
	if primary:
		doc.append(
			"hero_images",
			{
				"image": primary,
				"image_alt": _text(hero.get("imageAlt")),
				"note": _text(hero.get("note")),
				"image_focus": hero_image_focus_label(hero.get("imageFocus")),
			},
		)
	for item in hero.get("carousel") or []:
		parsed = parse_hero_carousel_item(item)
		if parsed:
			path, note, focus = parsed
			doc.append(
				"hero_images",
				{
					"image": path,
					"note": note,
					"image_alt": "",
					"image_focus": hero_image_focus_label(focus),
				},
			)


def apply_home_about(doc, data: dict):
	about = data.get("about") or {}
	doc.about_title = _text(about.get("title"))
	doc.about_body = paragraphs_to_html(about.get("paragraphs"))


def apply_home_impacts(doc, data: dict):
	doc.set("impacts", [])
	for row in data.get("impacts") or []:
		doc.append("impacts", {"value": _text(row.get("value")), "metric_label": _text(row.get("label"))})


def apply_home_our_work(doc, data: dict):
	our_work = data.get("ourWork") or {}
	doc.homepage_summary = _text(our_work.get("homepageSummary"))
	doc.page_introduction = _text(our_work.get("pageIntroduction"))
	doc.set("expertise", [])
	for row in our_work.get("expertise") or []:
		doc.append("expertise", {"title": _text(row.get("title")), "description": _text(row.get("description"))})
	doc.image = _text(our_work.get("image"))
	doc.image_alt = _text(our_work.get("imageAlt"))
	doc.page_conclusion = _text(our_work.get("pageConclusion"))


def apply_home_partners(doc, data: dict):
	doc.set("partners", [])
	for row in data.get("partners") or []:
		active = row.get("active")
		doc.append(
			"partners",
			{
				"partner_name": _text(row.get("name")),
				"url": _text(row.get("url")),
				"logo": _text(row.get("logo")),
				"show_on_website": 0 if active is False else 1,
				"sort_order": cint(row.get("order")),
			},
		)


def apply_privacy(doc, data: dict):
	reviewed = data.get("lastReviewed")
	doc.last_reviewed = getdate(reviewed) if reviewed else None
	doc.status = PUBLISHED
	doc.body = body_sections_to_html(data.get("sections"))


def apply_publication(doc, data: dict, slug: str):
	video = data.get("video") or {}
	doc.title = _text(data.get("title"))
	doc.slug = slug
	published_on = data.get("publishedAt")
	doc.published_on = getdate(published_on) if published_on else None
	year = data.get("year")
	doc.year = cint(year) if year not in (None, "") else None
	doc.publication_type = normalize_publication_type(data.get("type"))
	doc.service_area = _text(data.get("serviceArea"))
	doc.featured = 1 if data.get("featured") else 0
	doc.summary = _text(data.get("summary"))
	doc.cover = _text(data.get("cover"))
	doc.cover_alt = _text(data.get("coverAlt"))
	doc.file_url = _text(data.get("fileUrl"))
	doc.page_url = _text(data.get("pageUrl"))
	doc.external_url = _text(data.get("externalUrl"))
	doc.video_embed_url = _text(video.get("embedUrl"))
	doc.video_title = _text(video.get("title"))
	doc.video_caption = _text(video.get("caption"))
	if data.get("draft") is True:
		doc.status = DRAFT
		doc.show_on_website = 0
	else:
		doc.status = PUBLISHED
		doc.show_on_website = 1
	doc.set("topics", [])
	for topic in data.get("topics") or []:
		if _text(topic):
			doc.append("topics", {"topic": _text(topic)})
	doc.body = body_sections_to_html(data.get("body"))


def apply_employee_profile(doc, data: dict, slug: str):
	active = data.get("active")
	doc.role = _text(data.get("role"))
	doc.slug = slug
	doc.sort_order = cint(data.get("order"))
	if active is False:
		doc.website_status = UNPUBLISHED
		doc.show_on_website = 0
	else:
		doc.website_status = PUBLISHED
		doc.show_on_website = 1
	doc.portrait = _text(data.get("image"))
	doc.use_employee_image = 0
	doc.linkedin = _text(data.get("linkedin"))


def find_employee(slug: str, display_name: str = "") -> str | None:
	"""Match website team content to one existing Employee without changing HR identity."""
	by_slug = frappe.get_all("Employee", filters={"slug": slug}, pluck="name")
	if len(by_slug) > 1:
		frappe.throw(_("Multiple Employees use website slug '{0}'.").format(slug))
	if by_slug:
		return by_slug[0]

	name = _text(display_name)
	if not name:
		return None
	by_name = frappe.get_all("Employee", filters={"employee_name": name}, pluck="name")
	if len(by_name) > 1:
		frappe.throw(_("Multiple Employees are named '{0}'. Resolve the duplicate before loading website content.").format(name))
	return by_name[0] if by_name else None


def apply_enterprise(doc, data: dict, slug: str):
	active = data.get("active")
	# Keep an existing CRM name; only fill when creating or blank.
	incoming = _text(data.get("name")) or slug
	if not _text(doc.enterprise_name):
		doc.enterprise_name = incoming
	doc.sort_order = cint(data.get("order"))
	if active is False:
		doc.website_status = UNPUBLISHED
		doc.show_on_website = 0
	else:
		doc.website_status = PUBLISHED
		doc.show_on_website = 1


def find_enterprise(slug: str, display_name: str = "") -> str | None:
	"""Match content to Cubenet Enterprise by derived slug or case-insensitive name."""
	from opero.opero.doctype.enterprise.enterprise import enterprise_content_slug

	display = _text(display_name)
	for row in frappe.get_all("Enterprise", fields=["name", "enterprise_name"]):
		ename = _text(row.enterprise_name)
		if not ename:
			continue
		if enterprise_content_slug(ename) == slug:
			return row.name
		if display and ename.casefold() == display.casefold():
			return row.name
	return None


def attach_content_logo(doc, logo_path: str, repo: ContentRepo | None) -> bool:
	"""Download `/media/...` logos into Desk File attachments. Returns True if doc.logo changed."""
	return attach_content_image(doc, "logo", logo_path, repo)


def attach_content_image(doc, field: str, logo_path: str, repo: ContentRepo | None) -> bool:
	"""Resolve repository media into a public Desk attachment for an image field."""
	logo_path = _text(logo_path)
	previous = _text(doc.get(field))
	if not logo_path:
		doc.set(field, "")
		return previous != ""

	if logo_path.startswith(("/files/", "/private/files/")):
		doc.set(field, logo_path)
		return previous != logo_path

	repo_path = logo_path[1:] if logo_path.startswith("/") else logo_path
	legacy_portrait = field == "portrait" and repo_path.startswith("team/")
	if not repo_path.startswith("media/") and not legacy_portrait:
		doc.set(field, logo_path)
		return previous != _text(doc.get(field))

	filename = os.path.basename(repo_path)
	if not filename or filename in (".", ".."):
		doc.set(field, f"/{repo_path}")
		return previous != _text(doc.get(field))

	existing = frappe.db.get_value(
		"File",
		{
			"attached_to_doctype": doc.doctype,
			"attached_to_name": doc.name,
			"file_name": filename,
		},
		"file_url",
	)
	if existing:
		doc.set(field, existing)
		return previous != existing

	if repo and legacy_portrait:
		site_repo = ContentRepo(repo.token, "opero-con/opero-site", repo.base_branch)
		blob = site_repo.get_bytes(f"public/{repo_path}", site_repo.base_branch)
	else:
		blob = repo.get_bytes(repo_path, repo.base_branch) if repo else None
	if not blob:
		if repo and field == "portrait":
			frappe.throw(_("Website portrait file is missing from the content repository: {0}").format(repo_path))
		doc.set(field, f"/{repo_path}")
		return previous != _text(doc.get(field))

	file_doc = save_file(filename, blob, doc.doctype, doc.name, is_private=0)
	if field == "portrait" and file_doc.file_name != filename:
		# Keep the source attachment label even when Frappe hashes its storage URL.
		file_doc.db_set("file_name", filename)
	doc.set(field, file_doc.file_url)
	return previous != _text(doc.get(field))


def _enterprise_name_for_slug(slug: str) -> str | None:
	return find_enterprise(slug)


def matches_website(doc, path: str, text: str) -> bool:
	if doc.is_new():
		return False
	planned = doc.to_site_frontmatter()
	if doc.doctype == "Employee":
		incoming_image = _text(parse_frontmatter(text).get("image"))
		if incoming_image.lstrip("/").startswith(("media/", "team/")) and frappe.db.exists(
			"File", {"attached_to_doctype": doc.doctype, "attached_to_name": doc.name,
			"file_name": os.path.basename(incoming_image), "file_url": planned.get("image")}
		):
			planned["image"] = incoming_image
	return same_managed_content(path, text, to_markdown(planned))


def _content_snapshot(value):
	"""Compare section values without generated child-row bookkeeping."""
	if isinstance(value, dict):
		return {
			key: _content_snapshot(item) for key, item in value.items()
			if key not in {"name", "creation", "modified", "modified_by", "owner", "parent", "parenttype", "parentfield", "idx", "__islocal", "__unsaved"}
		}
	if isinstance(value, list):
		return [_content_snapshot(item) for item in value]
	return value


def load_files(files: dict[str, str], repo: ContentRepo | None = None) -> dict[str, int]:
	counts = {"settings": 0, "home": 0, "privacy": 0, "publications": 0, "team": 0, "enterprises": 0}
	previous_syncing = frappe.flags.opero_site_syncing
	frappe.flags.opero_site_syncing = True
	try:
		for path, text in files.items():
			if path == "content/settings/general.md":
				doc = frappe.get_single("Site Settings")
				if matches_website(doc, path, text):
					continue
				apply_settings(doc, parse_frontmatter(text))
				doc.save(ignore_permissions=True)
				counts["settings"] += 1
			elif path == "content/homepage/home.md":
				home = frappe.get_single("Home Page")
				if matches_website(home, path, text):
					continue
				data = parse_frontmatter(text)
				for section_doctype, apply_section in (
					("Hero", apply_home_hero),
					("About", apply_home_about),
					("Impacts", apply_home_impacts),
					("Our Work", apply_home_our_work),
					("Partners", apply_home_partners),
				):
					section_doc = frappe.get_single(section_doctype)
					before = _content_snapshot(section_doc.as_dict())
					apply_section(section_doc, data)
					if before != _content_snapshot(section_doc.as_dict()):
						section_doc.save(ignore_permissions=True)
				home = frappe.get_single("Home Page")
				home.status = PUBLISHED
				home.save(ignore_permissions=True)
				counts["home"] += 1
			elif path == "content/privacy/privacy.md":
				doc = frappe.get_single("Privacy policy")
				if matches_website(doc, path, text):
					continue
				apply_privacy(doc, parse_frontmatter(text))
				doc.save(ignore_permissions=True)
				counts["privacy"] += 1
			elif path.startswith("content/publications/") and path.endswith(".md"):
				slug = slug_from_path(path)
				if frappe.db.exists("Publication", slug):
					doc = frappe.get_doc("Publication", slug)
				else:
					doc = frappe.new_doc("Publication")
				if matches_website(doc, path, text):
					continue
				apply_publication(doc, parse_frontmatter(text), slug)
				doc.save(ignore_permissions=True)
				counts["publications"] += 1
			elif path.startswith("content/team/") and path.endswith(".md"):
				slug = slug_from_path(path)
				data = parse_frontmatter(text)
				name = find_employee(slug, _text(data.get("name")))
				if name:
					doc = frappe.get_doc("Employee", name)
				else:
					frappe.throw(
						_("No Employee matches website team member '{0}'. Create the Employee before loading website content.").format(
							_text(data.get("name")) or slug
						)
					)
				if matches_website(doc, path, text):
					if repo and not doc.use_employee_image and attach_content_image(doc, "portrait", _text(data.get("image")), repo):
						doc.save(ignore_permissions=True)
						counts["team"] += 1
					continue
				apply_employee_profile(doc, data, slug)
				if repo:
					attach_content_image(doc, "portrait", _text(data.get("image")), repo)
				doc.save(ignore_permissions=True)
				counts["team"] += 1
			elif path.startswith("content/enterprises/") and path.endswith(".md"):
				slug = slug_from_path(path)
				data = parse_frontmatter(text)
				name = find_enterprise(slug, _text(data.get("name")))
				if name:
					doc = frappe.get_doc("Enterprise", name)
				else:
					doc = frappe.new_doc("Enterprise")
				if matches_website(doc, path, text):
					continue
				apply_enterprise(doc, data, slug)
				if doc.is_new():
					doc.insert(ignore_permissions=True)
				else:
					doc.save(ignore_permissions=True)
				if attach_content_logo(doc, _text(data.get("logo")), repo):
					doc.save(ignore_permissions=True)
				counts["enterprises"] += 1
	finally:
		frappe.flags.opero_site_syncing = previous_syncing
		if sum(counts.values()):
			clear_pending_cache()
	return counts


@frappe.whitelist()
def load_from_website() -> dict:
	if not frappe.has_permission("Site Settings", "write"):
		frappe.throw(_("Not permitted to load Opero Site content."))
	repo = content_repo_from_conf()
	try:
		paths = repo.list_markdown("content/", repo.base_branch)
		files = repo.existing_files(paths, repo.base_branch)
		counts = load_files(files, repo=repo)
	except GithubError as exc:
		frappe.throw(str(exc))
	total = sum(counts.values())
	return {
		"counts": counts,
		"message": _("Loaded {0} changed content files from the public site repository. Unchanged content was skipped.").format(total),
	}
