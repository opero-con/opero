from secrets import randbelow

import frappe
from frappe.contacts.address_and_contact import delete_contact_and_address, load_address_and_contact
from frappe.model.document import Document


def make_enterprise_name():
	"""E + five random digits, like Contact/Supplier opaque IDs with a readable title."""
	for _ in range(50):
		name = f"E{randbelow(100000):05d}"
		if not frappe.db.exists("Enterprise", name):
			return name
	frappe.throw(frappe._("Could not allocate a unique Enterprise ID. Try again."))


class Enterprise(Document):
	def onload(self):
		load_address_and_contact(self)

	def autoname(self):
		self.name = make_enterprise_name()

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
