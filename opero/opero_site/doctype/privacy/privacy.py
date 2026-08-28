from __future__ import annotations

from frappe.model.document import Document
from frappe.utils import getdate

from opero.opero_site.publish_status import TO_PUBLISH, apply_publish_status
from opero.opero_site.utils import body_sections


class Privacy(Document):
	def validate(self):
		apply_publish_status(self, default=TO_PUBLISH)
		body_sections(self.sections)

	def to_site_frontmatter(self) -> dict:
		return {
			"lastReviewed": getdate(self.last_reviewed).isoformat() if self.last_reviewed else "",
			"sections": body_sections(self.sections),
		}
