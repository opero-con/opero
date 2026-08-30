from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.utils import cstr

_PUBLIC_URL = re.compile(r"^https?://\S+\.\S+")

PUBLICATION_TYPES = (
	"Case study",
	"Digest",
	"Newsletter",
	"Overview",
	"Project",
)

PUBLICATION_TYPE_ALIASES = {
	"Portfolio": "Overview",
}


def normalize_publication_type(value: str) -> str:
	trimmed = cstr(value).strip()
	return PUBLICATION_TYPE_ALIASES.get(trimmed, trimmed)


def slugify(text: str) -> str:
	value = cstr(text).strip().lower()
	value = re.sub(r"[^a-z0-9]+", "-", value)
	return value.strip("-")


def optional_url(value: str, label: str) -> str:
	url = cstr(value).strip()
	if not url:
		return ""
	if _PUBLIC_URL.match(url) or (url.startswith("/") and not url.startswith("//")):
		return url
	frappe.throw(
		_("{0} must be a full http(s) URL, a site path such as /downloads/file.pdf, or left blank.").format(
			label
		)
	)


def lines(value: str) -> list[str]:
	return [line.strip() for line in cstr(value).splitlines() if line.strip()]


def paragraphs(value: str) -> list[str]:
	blocks = re.split(r"\n\s*\n", cstr(value).strip())
	return [block.strip() for block in blocks if block.strip()]


def hero_carousel_entry(image: str, note: str = "") -> dict | None:
	path = cstr(image).strip()
	if not path:
		return None
	entry = {"image": path}
	label = cstr(note).strip()
	if label:
		entry["note"] = label
	return entry


def parse_hero_carousel_item(item) -> tuple[str, str] | None:
	if isinstance(item, str):
		path = cstr(item).strip()
		return (path, "") if path else None
	if isinstance(item, dict):
		path = cstr(item.get("image")).strip()
		if not path:
			return None
		return path, cstr(item.get("note")).strip()
	return None


def parse_links(value: str) -> list[dict]:
	out = []
	for line in lines(value):
		if " | " in line:
			label, href = line.split(" | ", 1)
		elif "\t" in line:
			label, href = line.split("\t", 1)
		else:
			frappe.throw(_("Each body link must be `Label | https://example.com`."))
		href = optional_url(href.strip(), _("Link URL"))
		label = label.strip()
		if not label or not href:
			frappe.throw(_("Each body link needs a label and a URL."))
		out.append({"label": label, "href": href})
	return out


def body_sections(rows) -> list[dict]:
	out = []
	for row in rows or []:
		section = {}
		heading = cstr(row.heading).strip()
		if heading:
			section["heading"] = heading
		paras = paragraphs(row.paragraphs)
		if paras:
			section["paragraphs"] = paras
		bullets = lines(row.bullets)
		if bullets:
			section["bullets"] = bullets
		if row.links:
			parsed = parse_links(row.links)
			if parsed:
				section["links"] = parsed
		if section:
			out.append(section)
	return out
