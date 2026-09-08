from secrets import randbelow

import frappe
from frappe import _
from frappe.contacts.address_and_contact import delete_contact_and_address, load_address_and_contact
from frappe.model.document import Document
from frappe.utils import cint, cstr

from opero.opero_site.publish_status import apply_publish_status, is_on_site
from opero.opero_site.utils import optional_url, slugify


def make_enterprise_name():
	"""E + five random digits, like Contact/Supplier opaque IDs with a readable title."""
	for _ in range(50):
		name = f"E{randbelow(100000):05d}"
		if not frappe.db.exists("Enterprise", name):
			return name
	frappe.throw(frappe._("Could not allocate a unique Enterprise ID. Try again."))


def enterprise_content_slug(enterprise_name: str) -> str:
	"""Filename id for `content/enterprises/<slug>.md`, derived from the display name."""
	return slugify(enterprise_name)


class Enterprise(Document):
	def onload(self):
		load_address_and_contact(self)

	def autoname(self):
		self.name = make_enterprise_name()

	def validate(self):
		self.enterprise_name = cstr(self.enterprise_name).strip()
		if not self.enterprise_name:
			frappe.throw(_("Enterprise Name is required."))
		if not enterprise_content_slug(self.enterprise_name):
			frappe.throw(_("Enterprise Name must contain at least one letter or number."))

		self.website = optional_url(self.website, "Website")
		apply_publish_status(self)
		self.sort_order = cint(self.sort_order)

	def to_site_frontmatter(self) -> dict:
		"""YAML frontmatter for opero-content `content/enterprises/<slug>.md`."""
		payload = {
			"name": self.enterprise_name,
			"order": cint(self.sort_order),
			"active": is_on_site(self),
		}
		if self.logo:
			payload["logo"] = cstr(self.logo)
		return payload

	def on_trash(self):
		if self.enterprise_primary_contact:
			self.db_set("enterprise_primary_contact", None)
		if self.enterprise_primary_address:
			self.db_set("enterprise_primary_address", None)

		delete_contact_and_address("Enterprise", self.name)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_enterprise_primary(doctype, txt, searchfield, start, page_len, filters):
	enterprise = filters.get("enterprise")
	type_doctype_name = filters.get("type")
	type_doctype = frappe.qb.DocType(type_doctype_name)
	dynamic_link = frappe.qb.DocType("Dynamic Link")

	query = (
		frappe.qb.from_(type_doctype)
		.join(dynamic_link)
		.on(type_doctype.name == dynamic_link.parent)
		.select(type_doctype.name)
		.where(
			(dynamic_link.link_name == enterprise)
			& (dynamic_link.link_doctype == "Enterprise")
			& (type_doctype.name.like(f"%{txt}%"))
		)
	)

	if type_doctype_name == "Contact":
		query = query.select(type_doctype.email_id)

	return query.run()
