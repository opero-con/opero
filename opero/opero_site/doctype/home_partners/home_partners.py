from __future__ import annotations

from frappe.model.document import Document
from frappe.utils import cint, cstr

from opero.opero_site.utils import optional_url


class HomePartners(Document):
	def validate(self):
		for row in self.partners or []:
			row.url = optional_url(row.url, "Partner URL")
			if row.show_on_website is None:
				row.show_on_website = 1
			row.sort_order = cint(row.sort_order)

	def to_site_frontmatter(self) -> list[dict]:
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
		return partners
