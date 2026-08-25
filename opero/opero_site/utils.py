from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.utils import cstr

_PUBLIC_URL = re.compile(r"^https?://\S+\.\S+")


def slugify(text: str) -> str:
	value = cstr(text).strip().lower()
	value = re.sub(r"[^a-z0-9]+", "-", value)
	return value.strip("-")


def optional_url(value: str, label: str) -> str:
	url = cstr(value).strip()
	if not url:
		return ""
	if not _PUBLIC_URL.match(url):
		frappe.throw(_("{0} must be a full http(s) URL, or left blank.").format(label))
	return url


def lines(value: str) -> list[str]:
	return [line.strip() for line in cstr(value).splitlines() if line.strip()]


def paragraphs(value: str) -> list[str]:
	blocks = re.split(r"\n\s*\n", cstr(value).strip())
	return [block.strip() for block in blocks if block.strip()]


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
