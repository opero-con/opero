from __future__ import annotations

import re
from datetime import date, datetime

import yaml
from frappe.utils import cint, cstr, flt, getdate

from opero.opero_site.utils import hero_carousel_entry, parse_hero_carousel_item
from opero.opero_site.utils import lines as split_lines
from opero.opero_site.utils import paragraphs as split_paragraphs

_FRONTMATTER = re.compile(r"^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n([\s\S]*))?$")


def to_markdown(frontmatter: dict, body: str = "") -> str:
	payload = yaml.safe_dump(
		frontmatter,
		sort_keys=False,
		allow_unicode=True,
		default_flow_style=False,
	)
	text = f"---\n{payload}---\n"
	if body and body.strip():
		if not body.endswith("\n"):
			body += "\n"
		text += body
	return text


def parse_frontmatter(text: str) -> dict:
	return split_markdown(text)[0]


def split_markdown(text: str) -> tuple[dict, str]:
	match = _FRONTMATTER.match(text)
	if not match:
		raise ValueError("Markdown is missing YAML frontmatter.")
	data = yaml.safe_load(match.group(1))
	if not isinstance(data, dict):
		raise ValueError("Frontmatter must be a mapping.")
	return data, match.group(2) or ""


def same_managed_content(path: str, existing: str, planned: str) -> bool:
	"""True when Desk output matches GitHub for fields Opero Site manages.

	Ignores YAML quoting, key order, derived `year`, homepage `team`, and other
	keys that Load does not import. After Load from website content, pending
	should be empty even though `yaml.safe_dump` is not byte-identical.
	"""
	if existing == planned:
		return True
	try:
		old, _old_body = split_markdown(existing)
		new, _new_body = split_markdown(planned)
	except ValueError:
		return False
	return canonical_frontmatter(path, old) == canonical_frontmatter(path, new)


def preserve_unmanaged_frontmatter(existing: str, planned: str) -> str:
	"""Keep GitHub-only keys (homepage `team`, extra publication fields) on publish."""
	try:
		old, old_body = split_markdown(existing)
		new, new_body = split_markdown(planned)
	except ValueError:
		return planned
	merged = {}
	for key, value in old.items():
		if key in new:
			merged[key] = new.pop(key)
		else:
			merged[key] = value
	merged.update(new)
	body = new_body if new_body.strip() else old_body
	return to_markdown(merged, body)


def canonical_frontmatter(path: str, data: dict) -> dict:
	if path == "content/homepage/home.md":
		shaped = _canonical_home(data)
	elif path == "content/settings/general.md":
		shaped = _canonical_settings(data)
	elif path == "content/privacy/privacy.md":
		shaped = _canonical_privacy(data)
	elif path.startswith("content/publications/"):
		shaped = _canonical_publication(data, _slug_from_path(path))
	elif path.startswith("content/team/"):
		shaped = _canonical_team(data)
	else:
		shaped = dict(data)
	return _compact(shaped)


def _slug_from_path(path: str) -> str:
	return path.rsplit("/", 1)[-1].removesuffix(".md")


def _text(value) -> str:
	return cstr(value).strip()


def _iso_date(value) -> str:
	if value in (None, ""):
		return ""
	if isinstance(value, datetime):
		value = value.date()
	if isinstance(value, date):
		return value.isoformat()
	return getdate(value).isoformat()


def _as_lines(value) -> list[str]:
	if isinstance(value, list):
		return [_text(item) for item in value if _text(item)]
	return split_lines(value)


def _as_paragraphs(value) -> list[str]:
	if isinstance(value, list):
		value = "\n\n".join(_text(item) for item in value if _text(item))
	return split_paragraphs(value)


def _as_links(value) -> list[dict]:
	if not value:
		return []
	out = []
	if isinstance(value, list):
		for item in value:
			if isinstance(item, dict):
				label = _text(item.get("label"))
				href = _text(item.get("href") or item.get("url"))
				if label and href:
					out.append({"label": label, "href": href})
	return out


def _canonical_sections(rows) -> list[dict]:
	out = []
	for row in rows or []:
		if not isinstance(row, dict):
			continue
		section = {}
		heading = _text(row.get("heading"))
		if heading:
			section["heading"] = heading
		paragraphs = _as_paragraphs(row.get("paragraphs"))
		if paragraphs:
			section["paragraphs"] = paragraphs
		bullets = _as_lines(row.get("bullets"))
		if bullets:
			section["bullets"] = bullets
		links = _as_links(row.get("links"))
		if links:
			section["links"] = links
		if section:
			out.append(section)
	return out


def _canonical_home(data: dict) -> dict:
	hero_in = data.get("hero") or {}
	hero = {
		"eyebrow": _text(hero_in.get("eyebrow")),
		"title": _text(hero_in.get("title")),
		"description": _text(hero_in.get("description")),
	}
	if hero_in.get("image"):
		hero["image"] = cstr(hero_in.get("image"))
	if _text(hero_in.get("imageAlt")):
		hero["imageAlt"] = _text(hero_in.get("imageAlt"))
	if _text(hero_in.get("note")):
		hero["note"] = _text(hero_in.get("note"))
	carousel = []
	for item in hero_in.get("carousel") or []:
		parsed = parse_hero_carousel_item(item)
		if not parsed:
			continue
		entry = hero_carousel_entry(*parsed)
		if entry:
			carousel.append(entry)
	if carousel:
		hero["carousel"] = carousel

	about_in = data.get("about") or {}
	projects = []
	for row in data.get("projects") or []:
		if not isinstance(row, dict):
			continue
		project = {
			"slug": _text(row.get("slug")),
			"title": _text(row.get("title")),
			"shortTitle": _text(row.get("shortTitle")),
			"eyebrow": _text(row.get("eyebrow")),
			"summary": _text(row.get("summary")),
			"highlights": _as_lines(row.get("highlights")),
		}
		if row.get("image"):
			project["image"] = cstr(row.get("image"))
		if _text(row.get("imageAlt")):
			project["imageAlt"] = _text(row.get("imageAlt"))
		if row.get("metricValue") or row.get("metricLabel"):
			project["metricValue"] = _text(row.get("metricValue"))
			project["metricLabel"] = _text(row.get("metricLabel"))
		if row.get("detailUrl"):
			project["detailUrl"] = _text(row.get("detailUrl"))
		projects.append(project)

	partners = []
	raw_partners = [row for row in (data.get("partners") or []) if isinstance(row, dict)]
	for row in sorted(raw_partners, key=lambda item: cint(item.get("order"))):
		if row.get("active") is False:
			continue
		partner = {"name": _text(row.get("name"))}
		if row.get("url"):
			partner["url"] = _text(row.get("url"))
		if row.get("logo"):
			partner["logo"] = cstr(row.get("logo"))
		partners.append(partner)

	return {
		"hero": hero,
		"about": {
			"title": _text(about_in.get("title")),
			"paragraphs": _as_paragraphs(about_in.get("paragraphs")),
		},
		"pillars": [
			{"title": _text(row.get("title")), "description": _text(row.get("description"))}
			for row in (data.get("pillars") or [])
			if isinstance(row, dict)
		],
		"impacts": [
			{"value": _text(row.get("value")), "label": _text(row.get("label"))}
			for row in (data.get("impacts") or [])
			if isinstance(row, dict)
		],
		"projects": projects,
		"partners": partners,
	}


def _canonical_settings(data: dict) -> dict:
	seo_in = data.get("seo") or {}
	offices = []
	for row in data.get("offices") or []:
		if not isinstance(row, dict):
			continue
		office = {
			"city": _text(row.get("city")),
			"country": _text(row.get("country")),
		}
		if _text(row.get("label")):
			office["label"] = _text(row.get("label"))
		if _text(row.get("building")):
			office["building"] = _text(row.get("building"))
		if _text(row.get("street")):
			office["street"] = _text(row.get("street"))
		offices.append(office)
	seo = {
		"title": _text(seo_in.get("title")),
		"description": _text(seo_in.get("description")),
		"canonicalUrl": _text(seo_in.get("canonicalUrl")),
	}
	if seo_in.get("ogImage"):
		seo["ogImage"] = cstr(seo_in.get("ogImage"))
	payload = {
		"organizationName": _text(data.get("organizationName")),
		"email": _text(data.get("email")),
		"communicationsEmail": _text(data.get("communicationsEmail")),
		"phone": _text(data.get("phone")),
		"trainingPhone": _text(data.get("trainingPhone")),
		"offices": offices,
		"seo": seo,
	}
	if data.get("linkedinUrl"):
		payload["linkedinUrl"] = _text(data.get("linkedinUrl"))
	if data.get("twitterUrl"):
		payload["twitterUrl"] = _text(data.get("twitterUrl"))
	return payload


def _canonical_privacy(data: dict) -> dict:
	return {
		"lastReviewed": _iso_date(data.get("lastReviewed")),
		"sections": _canonical_sections(data.get("sections")),
	}


def _canonical_publication(data: dict, slug: str) -> dict:
	published = _iso_date(data.get("publishedAt"))
	year = data.get("year")
	if year in (None, ""):
		year = int(published[:4]) if published else None
	else:
		year = cint(year)
	payload = {
		"slug": _text(data.get("slug")) or slug,
		"title": _text(data.get("title")),
		"publishedAt": published,
		"type": _text(data.get("type")),
		"summary": _text(data.get("summary")),
		"topics": [_text(topic) for topic in (data.get("topics") or []) if _text(topic)],
		"featured": bool(data.get("featured")),
	}
	if year:
		payload["year"] = year
	if _text(data.get("serviceArea")):
		payload["serviceArea"] = _text(data.get("serviceArea"))
	if data.get("cover"):
		payload["cover"] = cstr(data.get("cover"))
	if _text(data.get("coverAlt")):
		payload["coverAlt"] = _text(data.get("coverAlt"))
	if data.get("fileUrl"):
		payload["fileUrl"] = _text(data.get("fileUrl"))
	if data.get("pageUrl"):
		payload["pageUrl"] = _text(data.get("pageUrl"))
	if data.get("externalUrl"):
		payload["externalUrl"] = _text(data.get("externalUrl"))
	video_in = data.get("video") or {}
	if video_in.get("embedUrl"):
		video = {
			"embedUrl": _text(video_in.get("embedUrl")),
			"title": _text(video_in.get("title")),
		}
		if _text(video_in.get("caption")):
			video["caption"] = _text(video_in.get("caption"))
		payload["video"] = video
	body = _canonical_sections(data.get("body"))
	if body:
		payload["body"] = body
	return payload


def _canonical_team(data: dict) -> dict:
	payload = {
		"name": _text(data.get("name")),
		"role": _text(data.get("role")),
		"image": cstr(data.get("image")),
		"imageAlt": _text(data.get("imageAlt")),
		"order": cint(data.get("order")),
		"active": False if data.get("active") is False else True,
	}
	if data.get("linkedin"):
		payload["linkedin"] = _text(data.get("linkedin"))
	if _text(data.get("imagePosition")):
		payload["imagePosition"] = _text(data.get("imagePosition"))
	if data.get("imageScale") not in (None, ""):
		payload["imageScale"] = flt(data.get("imageScale"))
	if data.get("imageHoverScale") not in (None, ""):
		payload["imageHoverScale"] = flt(data.get("imageHoverScale"))
	return payload


def _compact(value):
	if isinstance(value, dict):
		out = {}
		for key, raw in value.items():
			item = _compact(raw)
			if not _is_empty(item):
				out[key] = item
		return out
	if isinstance(value, list):
		return [item for item in (_compact(v) for v in value) if not _is_empty(item)]
	if isinstance(value, str):
		return value.strip()
	if isinstance(value, datetime):
		return value.date().isoformat()
	if isinstance(value, date):
		return value.isoformat()
	if isinstance(value, float) and value.is_integer():
		return int(value)
	return value


def _is_empty(value) -> bool:
	return value is None or value == "" or value == [] or value == {}
