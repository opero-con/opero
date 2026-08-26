from __future__ import annotations

from frappe.model.document import Document
from frappe.utils import getdate

from opero.opero_site.utils import body_sections


class Privacy(Document):
	def validate(self):
		body_sections(self.sections)

	def to_site_frontmatter(self) -> dict:
		return {
			"lastReviewed": getdate(self.last_reviewed).isoformat() if self.last_reviewed else "",
			"sections": body_sections(self.sections),
		}
