from __future__ import annotations

from frappe.model.document import Document
from frappe.utils import cint, cstr

from opero.opero_site.utils import lines, optional_url


class HomePage(Document):
	def validate(self):
		for row in self.projects or []:
			row.detail_url = optional_url(row.detail_url, "Detail URL")
		for row in self.partners or []:
			row.url = optional_url(row.url, "Partner URL")
			if row.show_on_website is None:
				row.show_on_website = 1
			row.sort_order = cint(row.sort_order)

	def to_site_frontmatter(self) -> dict:
		"""YAML for opero-content `content/homepage/home.md`."""
		hero = {
			"eyebrow": cstr(self.hero_eyebrow).strip(),
			"title": cstr(self.hero_title).strip(),
			"description": cstr(self.hero_description).strip(),
		}
		if self.hero_image:
			hero["image"] = cstr(self.hero_image)
		if self.hero_image_alt:
			hero["imageAlt"] = cstr(self.hero_image_alt).strip()

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

		partners = []
		for row in sorted(self.partners or [], key=lambda item: cint(item.sort_order)):
			if not cint(row.show_on_website):
				continue
			partner = {"name": cstr(row.partner_name).strip()}
			if row.url:
				partner["url"] = row.url
			if row.logo:
				partner["logo"] = cstr(row.logo)
			partners.append(partner)

		return {
			"hero": hero,
			"about": {
				"title": cstr(self.about_title).strip(),
				"paragraphs": [
					cstr(row.paragraph).strip() for row in (self.about_paragraphs or []) if row.paragraph
				],
			},
			"pillars": [
				{"title": cstr(row.title).strip(), "description": cstr(row.description).strip()}
				for row in (self.pillars or [])
			],
			"impacts": [
				{"value": cstr(row.value).strip(), "label": cstr(row.metric_label).strip()}
				for row in (self.impacts or [])
			],
			"projects": projects,
			"partners": partners,
		}
