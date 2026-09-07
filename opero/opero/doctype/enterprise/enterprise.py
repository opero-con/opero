import frappe
from frappe.contacts.address_and_contact import delete_contact_and_address, load_address_and_contact
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series


class Enterprise(Document):
	def onload(self):
		load_address_and_contact(self)

	def autoname(self):
		set_name_by_naming_series(self)

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
