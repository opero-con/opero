from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr, getdate

from opero.opero_site.body_html import body_sections_to_html, html_to_body_sections
from opero.opero_site.cover_focal_point import CONTAIN, compute_cover_framing
from opero.opero_site.media import desk_file_url, read_desk_file
from opero.opero_site.publish_status import LIVE, apply_publish_status, get_publish_status
from opero.opero_site.utils import (
	normalize_publication_type,
	optional_url,
	slugify,
)


class Publication(Document):
	def _validate_links(self):
		self.publication_type = normalize_publication_type(self.publication_type)
		for row in self.topics or []:
			title = cstr(row.topic).strip()
			if title:
				row.topic = title
				_ensure_publication_topic(title)
		super()._validate_links()

	def validate(self):
		apply_publish_status(self)
		# The site bumps `views` with a bare UPDATE, so a form opened before a
		# visit would write its stale copy back and reset the count.
		if not self.is_new():
			self.views = cint(frappe.db.get_value("Publication", self.name, "views"))
		self.title = cstr(self.title).strip()
		self.set_slug()
		self.file_url = optional_url(self.file_url, "File URL")
		self.page_url = optional_url(self.page_url, "Page URL")
		self.external_url = optional_url(self.external_url, "External URL")
		self.video_embed_url = optional_url(self.video_embed_url, "Embed URL")
		if self.video_embed_url and not cstr(self.video_title).strip():
			frappe.throw(_("Accessible title is required when an embed URL is set."))
		if self.published_on:
			self.year = getdate(self.published_on).year
		self.move_long_summary_to_body()
		html_to_body_sections(self.body)
		self._set_cover_framing()

	def set_slug(self):
		"""Unique website slug; a blank one comes from the title, numbered when another publication has it."""
		typed = cstr(self.slug).strip()
		self.slug = slugify(typed or self.title)
		if not self.slug:
			frappe.throw(_("Slug must contain at least one letter or number."))
		if not typed:
			self.slug = self.get_free_slug(self.slug)
		elif self.is_slug_taken(self.slug):
			frappe.throw(_("Another publication already uses the slug {0}.").format(self.slug))
		self.validate_live_slug()

	def get_free_slug(self, base: str) -> str:
		slug, number = base, 1
		while self.is_slug_taken(slug):
			number += 1
			slug = f"{base}-{number}"
		return slug

	def is_slug_taken(self, slug: str) -> bool:
		return bool(frappe.db.exists("Publication", {"slug": slug, "name": ["!=", self.name or ""]}))

	def validate_live_slug(self):
		"""A live publication keeps its URL; unpublish and deploy it before changing the slug."""
		previous = None if self.is_new() else self.get_doc_before_save()
		if previous and previous.slug != self.slug and get_publish_status(previous) in LIVE:
			frappe.throw(_("{0} is on the website, so its slug can't change.").format(self.title))

	def move_long_summary_to_body(self):
		"""Move a multi-paragraph summary into an empty body, keeping its first paragraph."""
		if frappe.flags.get("opero_site_syncing") or html_to_body_sections(self.body):
			return
		paragraphs = [part.strip() for part in re.split(r"\n\s*\n", cstr(self.summary)) if part.strip()]
		if len(paragraphs) < 2:
			return
		self.body = body_sections_to_html([{"paragraphs": paragraphs}])
		self.summary = paragraphs[0]
		frappe.msgprint(
			_(
				"The summary had several paragraphs, so they now form the body. The first paragraph stays as the summary."
			),
			alert=True,
		)

	def _set_cover_framing(self):
		if frappe.flags.get("opero_site_syncing") or not self.has_value_changed("cover"):
			return
		self.cover_fit = self.cover_position = ""
		file_url = desk_file_url(self.cover) if self.cover else None
		if not file_url:
			return
		try:
			framing = compute_cover_framing(read_desk_file(file_url))
		except (OSError, ValueError):
			frappe.log_error(title="Cover framing")
			return
		self.cover_fit, self.cover_position = framing

	def to_site_frontmatter(self) -> dict:
		payload = {
			"slug": self.slug,
			"title": cstr(self.title).strip(),
			"publishedAt": getdate(self.published_on).isoformat() if self.published_on else "",
			"type": cstr(self.publication_type).strip(),
			"summary": cstr(self.summary).strip(),
			"topics": [cstr(row.topic).strip() for row in (self.topics or []) if row.topic],
			"featured": bool(cint(self.featured)),
		}
		if self.year:
			payload["year"] = cint(self.year)
		if self.service_area:
			payload["serviceArea"] = cstr(self.service_area).strip()
		if self.cover:
			payload["cover"] = cstr(self.cover)
		if self.cover_alt:
			payload["coverAlt"] = cstr(self.cover_alt).strip()
		if self.cover_position:
			payload["coverPosition"] = cstr(self.cover_position)
		if self.cover_fit == CONTAIN:
			payload["coverFit"] = CONTAIN
		if self.file_url:
			payload["fileUrl"] = self.file_url
		if self.page_url:
			payload["pageUrl"] = self.page_url
		if self.external_url:
			payload["externalUrl"] = self.external_url
		if self.video_embed_url:
			payload["video"] = {
				"embedUrl": self.video_embed_url,
				"title": cstr(self.video_title).strip(),
			}
			if self.video_caption:
				payload["video"]["caption"] = cstr(self.video_caption).strip()
		body = html_to_body_sections(self.body)
		if body:
			payload["body"] = body
		return payload


def _ensure_publication_topic(title: str) -> None:
	if frappe.db.exists("Publication Topic", title):
		return
	frappe.get_doc({"doctype": "Publication Topic", "title": title}).insert(
		ignore_permissions=True,
		ignore_if_duplicate=True,
	)
