from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr, getdate

from opero.opero_site.utils import body_sections, optional_url, slugify


class Publication(Document):
	def before_naming(self):
		self.title = cstr(self.title).strip()
		self.slug = slugify(self.slug or self.title)
		if not self.slug:
			frappe.throw(_("Slug must contain at least one letter or number."))

	def validate(self):
		self.title = cstr(self.title).strip()
		self.slug = slugify(self.slug or self.title)
		if not self.slug:
			frappe.throw(_("Slug must contain at least one letter or number."))
		self.file_url = optional_url(self.file_url, "File URL")
		self.external_url = optional_url(self.external_url, "External URL")
		self.video_embed_url = optional_url(self.video_embed_url, "Embed URL")
		if self.video_embed_url and not cstr(self.video_title).strip():
			frappe.throw(_("Accessible title is required when an embed URL is set."))
		if self.published_on:
			self.year = getdate(self.published_on).year
		body_sections(self.body)

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
		if self.file_url:
			payload["fileUrl"] = self.file_url
		if self.external_url:
			payload["externalUrl"] = self.external_url
		if self.video_embed_url:
			payload["video"] = {
				"embedUrl": self.video_embed_url,
				"title": cstr(self.video_title).strip(),
			}
			if self.video_caption:
				payload["video"]["caption"] = cstr(self.video_caption).strip()
		body = body_sections(self.body)
		if body:
			payload["body"] = body
		return payload
