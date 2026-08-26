from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr, flt

from opero.opero_site.utils import optional_url, slugify

__all__ = ["TeamMember", "slugify"]


class TeamMember(Document):
	def before_naming(self):
		self.member_name = cstr(self.member_name).strip()
		self.slug = slugify(self.slug or self.member_name)
		if not self.slug:
			frappe.throw(_("Slug must contain at least one letter or number."))

	def validate(self):
		self.member_name = cstr(self.member_name).strip()
		if not self.member_name:
			frappe.throw(_("Member Name is required."))

		self.slug = slugify(self.slug or self.member_name)
		if not self.slug:
			frappe.throw(_("Slug must contain at least one letter or number."))

		self.role = cstr(self.role).strip()
		self.linkedin = optional_url(self.linkedin, "LinkedIn URL")
		if self.show_on_website is None:
			self.show_on_website = 1
		self.sort_order = cint(self.sort_order)

	def to_site_frontmatter(self) -> dict:
		"""YAML frontmatter for opero-content `content/team/<slug>.md`."""
		payload = {
			"name": self.member_name,
			"role": cstr(self.role).strip(),
			"image": cstr(self.portrait),
			"imageAlt": cstr(self.portrait_alt).strip(),
			"order": cint(self.sort_order),
			"active": bool(cint(self.show_on_website)),
		}
		if self.linkedin:
			payload["linkedin"] = self.linkedin
		if self.portrait_position:
			payload["imagePosition"] = cstr(self.portrait_position).strip()
		if self.portrait_scale:
			payload["imageScale"] = flt(self.portrait_scale)
		if self.portrait_hover_scale:
			payload["imageHoverScale"] = flt(self.portrait_hover_scale)
		return payload
