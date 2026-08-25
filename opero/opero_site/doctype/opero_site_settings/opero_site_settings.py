from __future__ import annotations

from frappe.model.document import Document
from frappe.utils import cstr

from opero.opero_site.utils import optional_url


class OperoSiteSettings(Document):
	def validate(self):
		self.linkedin_url = optional_url(self.linkedin_url, "LinkedIn URL")
		self.twitter_url = optional_url(self.twitter_url, "Twitter/X URL")
		self.canonical_url = optional_url(self.canonical_url, "Canonical URL")

	def to_site_frontmatter(self) -> dict:
		offices = []
		for row in self.offices or []:
			office = {
				"city": cstr(row.city).strip(),
				"country": cstr(row.country).strip(),
			}
			if row.office_label:
				office["label"] = cstr(row.office_label).strip()
			if row.building:
				office["building"] = cstr(row.building).strip()
			if row.street:
				office["street"] = cstr(row.street).strip()
			offices.append(office)

		seo = {
			"title": cstr(self.seo_title).strip(),
			"description": cstr(self.seo_description).strip(),
			"canonicalUrl": cstr(self.canonical_url).strip(),
		}
		if self.og_image:
			seo["ogImage"] = cstr(self.og_image)

		payload = {
			"organizationName": cstr(self.organization_name).strip(),
			"email": cstr(self.email).strip(),
			"communicationsEmail": cstr(self.communications_email).strip(),
			"phone": cstr(self.phone).strip(),
			"trainingPhone": cstr(self.training_phone).strip(),
			"offices": offices,
			"seo": seo,
		}
		if self.linkedin_url:
			payload["linkedinUrl"] = self.linkedin_url
		if self.twitter_url:
			payload["twitterUrl"] = self.twitter_url
		return payload
