from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today

from opero.opero_site.body_html import html_to_body_sections, normalize_body_html
from opero.opero_site.publish_status import TO_PUBLISH, apply_publish_status


class Privacypolicy(Document):
	def validate(self):
		apply_publish_status(self, default=TO_PUBLISH)
		body_changed = self.has_value_changed("body")
		self.body = normalize_body_html(self.body)
		if frappe.flags.get("opero_site_syncing"):
			return
		if body_changed or not self.last_reviewed:
			self.last_reviewed = today()

	def to_site_frontmatter(self) -> dict:
		return {
			"lastReviewed": getdate(self.last_reviewed).isoformat() if self.last_reviewed else "",
			"sections": html_to_body_sections(self.body),
		}
