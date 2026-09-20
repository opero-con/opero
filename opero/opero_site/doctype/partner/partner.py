from __future__ import annotations

from secrets import randbelow

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr

from opero.opero_site.publish_status import apply_publish_status, is_on_site
from opero.opero_site.utils import optional_url, slugify


def partner_content_slug(partner_name: str) -> str:
	return slugify(partner_name)


def make_partner_name() -> str:
	"""P + five random digits, matching the standalone Enterprise ID pattern."""
	for _attempt in range(50):
		name = f"P{randbelow(100_000):05d}"
		if not frappe.db.exists("Partner", name):
			return name
	frappe.throw(_("Could not allocate a unique Partner ID. Try again."))


class Partner(Document):
	def autoname(self):
		self.name = make_partner_name()

	def validate(self):
		self.partner_name = cstr(self.partner_name).strip()
		if not self.partner_name:
			frappe.throw(_("Partner Name is required."))
		slug = partner_content_slug(self.partner_name)
		if not slug:
			frappe.throw(_("Partner Name must contain at least one letter or number."))
		self._check_slug_collision(slug)
		self.url = optional_url(self.url, "Partner URL")
		apply_publish_status(self)
		self.sort_order = cint(self.sort_order)

	def to_site_frontmatter(self) -> dict:
		payload = {"name": self.partner_name, "order": cint(self.sort_order), "active": is_on_site(self)}
		if self.url:
			payload["url"] = self.url
		if self.logo:
			payload["logo"] = cstr(self.logo)
		return payload

	def _check_slug_collision(self, slug: str) -> None:
		for other_name in frappe.get_all("Partner", filters={"name": ["!=", self.name]}, pluck="partner_name"):
			if partner_content_slug(other_name) == slug:
				frappe.throw(
					_("Another partner's name also maps to the website slug '{0}'. Rename one of them.").format(slug)
				)
