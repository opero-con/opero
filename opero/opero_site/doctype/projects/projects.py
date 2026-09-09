from __future__ import annotations

from frappe.model.document import Document
from frappe.utils import cstr

from opero.opero_site.utils import lines, optional_url


class Projects(Document):
	def validate(self):
		for row in self.projects or []:
			row.detail_url = optional_url(row.detail_url, "Detail URL")

	def to_site_frontmatter(self) -> list[dict]:
		projects = []
		for row in self.projects or []:
			project = {
				"slug": cstr(row.slug).strip(),
				"title": cstr(row.title).strip(),
				"shortTitle": cstr(row.short_title).strip(),
				"eyebrow": cstr(row.eyebrow).strip(),
				"summary": cstr(row.summary).strip(),
				"highlights": lines(row.highlights),
			}
			if row.image:
				project["image"] = cstr(row.image)
			if row.image_alt:
				project["imageAlt"] = cstr(row.image_alt).strip()
			if row.metric_value or row.metric_label:
				project["metricValue"] = cstr(row.metric_value).strip()
				project["metricLabel"] = cstr(row.metric_label).strip()
			if row.detail_url:
				project["detailUrl"] = row.detail_url
			projects.append(project)
		return projects
