from __future__ import annotations

from frappe.model.document import Document
from frappe.utils import getdate

from opero.opero_site.body_html import html_to_body_sections, normalize_body_html
from opero.opero_site.publish_status import TO_PUBLISH, apply_publish_status


class Privacy(Document):
	def validate(self):
		apply_publish_status(self, default=TO_PUBLISH)
		self.body = normalize_body_html(self.body)

	def to_site_frontmatter(self) -> dict:
		return {
			"lastReviewed": getdate(self.last_reviewed).isoformat() if self.last_reviewed else "",
			"sections": html_to_body_sections(self.body),
		}
