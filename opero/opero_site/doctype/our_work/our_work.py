from __future__ import annotations

from frappe.model.document import Document
from frappe.utils import cstr

from opero.opero_site.publish_status import TO_DEPLOY, apply_publish_status


class OurWork(Document):
	def validate(self):
		apply_publish_status(self, default=TO_DEPLOY)

	def to_site_frontmatter(self) -> dict:
		data = {"homepageSummary": cstr(self.homepage_summary).strip()} if self.homepage_summary else {}
		if self.page_introduction:
			data["pageIntroduction"] = cstr(self.page_introduction).strip()
		data["expertise"] = [
			{"title": cstr(row.title).strip(), "description": cstr(row.description).strip()}
			for row in (self.expertise or [])
		]
		if self.image:
			data["image"] = cstr(self.image)
		if self.image_alt:
			data["imageAlt"] = cstr(self.image_alt).strip()
		if self.page_conclusion:
			data["pageConclusion"] = cstr(self.page_conclusion).strip()
		return data
