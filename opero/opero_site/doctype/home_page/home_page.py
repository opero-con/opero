from __future__ import annotations

import frappe
from frappe.model.document import Document

from opero.opero_site.publish_status import TO_DEPLOY, apply_publish_status

HOME_SECTIONS = ("Home Hero", "Home About", "Home Pillars", "Home Impacts", "Home Projects", "Home Partners")


class HomePage(Document):
	def validate(self):
		apply_publish_status(self, default=TO_DEPLOY)

	def to_site_frontmatter(self) -> dict:
		"""YAML for opero-content `content/homepage/home.md`, assembled from the section singles."""
		hero, about, pillars, impacts, projects, partners = (
			frappe.get_single(name) for name in HOME_SECTIONS
		)
		return {
			"hero": hero.to_site_frontmatter(),
			"about": about.to_site_frontmatter(),
			"pillars": pillars.to_site_frontmatter(),
			"impacts": impacts.to_site_frontmatter(),
			"projects": projects.to_site_frontmatter(),
			"partners": partners.to_site_frontmatter(),
		}
