from __future__ import annotations

from frappe.model.document import Document
from frappe.utils import cstr

from opero.opero_site.body_html import html_to_paragraphs, normalize_paragraphs_html


class About(Document):
	def validate(self):
		self.about_body = normalize_paragraphs_html(self.about_body)

	def to_site_frontmatter(self) -> dict:
		return {
			"title": cstr(self.about_title).strip(),
			"paragraphs": html_to_paragraphs(self.about_body),
		}
