from __future__ import annotations

from frappe.model.document import Document
from frappe.utils import cstr


class Pillars(Document):
	def to_site_frontmatter(self) -> list[dict]:
		return [
			{"title": cstr(row.title).strip(), "description": cstr(row.description).strip()}
			for row in (self.pillars or [])
		]
