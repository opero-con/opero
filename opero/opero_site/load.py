from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, getdate

from opero.opero_site.body_html import body_sections_to_html
from opero.opero_site.github import GithubError
from opero.opero_site.markdown import parse_frontmatter
from opero.opero_site.publish import content_repo_from_conf
from opero.opero_site.publish_status import DRAFT, PUBLISHED, UNPUBLISHED
from opero.opero_site.utils import normalize_publication_type, parse_hero_carousel_item


def slug_from_path(path: str) -> str:
	return path.rsplit("/", 1)[-1].removesuffix(".md")


def _text(value) -> str:
	return cstr(value).strip()


def _join_paragraphs(value) -> str:
	if isinstance(value, list):
		return "\n\n".join(_text(item) for item in value if _text(item))
	return _text(value)


def _join_lines(value) -> str:
	if isinstance(value, list):
		return "\n".join(_text(item) for item in value if _text(item))
	return _text(value)


def _join_links(value) -> str:
	if not value:
		return ""
	lines = []
	for item in value:
		if isinstance(item, dict):
			label = _text(item.get("label"))
			href = _text(item.get("href") or item.get("url"))
			if label and href:
				lines.append(f"{label} | {href}")
		elif _text(item):
			lines.append(_text(item))
	return "\n".join(lines)


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
	doc.show_on_website = 1
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


def apply_home(doc, data: dict):
	hero = data.get("hero") or {}
	about = data.get("about") or {}
	doc.hero_eyebrow = _text(hero.get("eyebrow"))
	doc.hero_title = _text(hero.get("title"))
	doc.hero_description = _text(hero.get("description"))
	doc.status = PUBLISHED
	doc.show_on_website = 1
	doc.set("hero_images", [])
	primary = _text(hero.get("image"))
	if primary:
		doc.append(
			"hero_images",
			{
				"image": primary,
				"image_alt": _text(hero.get("imageAlt")),
				"note": _text(hero.get("note")),
			},
		)
	for item in hero.get("carousel") or []:
		parsed = parse_hero_carousel_item(item)
		if parsed:
			path, note = parsed
			doc.append("hero_images", {"image": path, "note": note, "image_alt": ""})
	doc.about_title = _text(about.get("title"))
	doc.set("about_paragraphs", [])
	for paragraph in about.get("paragraphs") or []:
		if _text(paragraph):
			doc.append("about_paragraphs", {"paragraph": _text(paragraph)})
	doc.set("pillars", [])
	for row in data.get("pillars") or []:
		doc.append("pillars", {"title": _text(row.get("title")), "description": _text(row.get("description"))})
	doc.set("impacts", [])
	for row in data.get("impacts") or []:
		doc.append("impacts", {"value": _text(row.get("value")), "metric_label": _text(row.get("label"))})
	doc.set("projects", [])
	for row in data.get("projects") or []:
		doc.append(
			"projects",
			{
				"slug": _text(row.get("slug")),
				"title": _text(row.get("title")),
				"short_title": _text(row.get("shortTitle")),
				"eyebrow": _text(row.get("eyebrow")),
				"summary": _text(row.get("summary")),
				"image": _text(row.get("image")),
				"image_alt": _text(row.get("imageAlt")),
				"highlights": _join_lines(row.get("highlights")),
				"metric_value": _text(row.get("metricValue")),
				"metric_label": _text(row.get("metricLabel")),
				"detail_url": _text(row.get("detailUrl")),
			},
		)
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
	doc.show_on_website = 1
	doc.set("sections", [])
	for row in data.get("sections") or []:
		doc.append(
			"sections",
			{
				"heading": _text(row.get("heading")),
				"paragraphs": _join_paragraphs(row.get("paragraphs")),
				"bullets": _join_lines(row.get("bullets")),
				"links": _join_links(row.get("links")),
			},
		)


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


def apply_team_member(doc, data: dict, slug: str):
	active = data.get("active")
	doc.member_name = _text(data.get("name"))
	doc.role = _text(data.get("role"))
	doc.slug = slug
	doc.sort_order = cint(data.get("order"))
	if active is False:
		doc.status = UNPUBLISHED
		doc.show_on_website = 0
	else:
		doc.status = PUBLISHED
		doc.show_on_website = 1
	doc.portrait = _text(data.get("image"))
	doc.portrait_alt = _text(data.get("imageAlt"))
	doc.portrait_position = _text(data.get("imagePosition"))
	doc.portrait_scale = flt(data.get("imageScale")) if data.get("imageScale") not in (None, "") else None
	doc.portrait_hover_scale = (
		flt(data.get("imageHoverScale")) if data.get("imageHoverScale") not in (None, "") else None
	)
	doc.linkedin = _text(data.get("linkedin"))


def load_files(files: dict[str, str]) -> dict[str, int]:
	counts = {"settings": 0, "home": 0, "privacy": 0, "publications": 0, "team": 0}
	for path, text in files.items():
		if path == "content/settings/general.md":
			doc = frappe.get_single("Site Settings")
			apply_settings(doc, parse_frontmatter(text))
			doc.save(ignore_permissions=True)
			counts["settings"] += 1
		elif path == "content/homepage/home.md":
			doc = frappe.get_single("Home Page")
			apply_home(doc, parse_frontmatter(text))
			doc.save(ignore_permissions=True)
			counts["home"] += 1
		elif path == "content/privacy/privacy.md":
			doc = frappe.get_single("Privacy")
			apply_privacy(doc, parse_frontmatter(text))
			doc.save(ignore_permissions=True)
			counts["privacy"] += 1
		elif path.startswith("content/publications/") and path.endswith(".md"):
			slug = slug_from_path(path)
			if frappe.db.exists("Publication", slug):
				doc = frappe.get_doc("Publication", slug)
			else:
				doc = frappe.new_doc("Publication")
			apply_publication(doc, parse_frontmatter(text), slug)
			doc.save(ignore_permissions=True)
			counts["publications"] += 1
		elif path.startswith("content/team/") and path.endswith(".md"):
			slug = slug_from_path(path)
			if frappe.db.exists("Team Member", slug):
				doc = frappe.get_doc("Team Member", slug)
			else:
				doc = frappe.new_doc("Team Member")
			apply_team_member(doc, parse_frontmatter(text), slug)
			doc.save(ignore_permissions=True)
			counts["team"] += 1
	return counts


@frappe.whitelist()
def load_from_website() -> dict:
	if not frappe.has_permission("Site Settings", "write"):
		frappe.throw(_("Not permitted to load Opero Site content."))
	repo = content_repo_from_conf()
	try:
		paths = repo.list_markdown("content/", repo.base_branch)
		files = repo.existing_files(paths, repo.base_branch)
		counts = load_files(files)
	except GithubError as exc:
		frappe.throw(str(exc))
	total = sum(counts.values())
	return {
		"counts": counts,
		"message": _("Loaded {0} content files from the public site repository.").format(total),
	}
