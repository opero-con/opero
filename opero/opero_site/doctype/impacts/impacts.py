from __future__ import annotations

from frappe.model.document import Document
from frappe.utils import cstr


class Impacts(Document):
	def to_site_frontmatter(self) -> list[dict]:
		return [
			{"value": cstr(row.value).strip(), "label": cstr(row.metric_label).strip()}
			for row in (self.impacts or [])
		]
