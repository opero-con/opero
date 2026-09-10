import frappe
from frappe.tests.utils import FrappeTestCase

from opero.opero.doctype.enterprise.enterprise import get_enterprise_primary


class TestEnterprise(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.savepoint("enterprise_test")
		self.prefix = "_Enterprise Test " + frappe.generate_hash(length=8)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="enterprise_test")

	def test_enterprise_uses_native_contact_links(self):
		enterprise = frappe.get_doc(
			{
				"doctype": "Enterprise",
				"enterprise_name": self.prefix,
				"status": "Onboarded",
			}
		).insert()
		self.assertRegex(enterprise.name, r"^E\d{5}$")
		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": self.prefix,
				"email_ids": [{"email_id": "enterprise@example.test", "is_primary": 1}],
				"phone_nos": [{"phone": "+254700000000", "is_primary_mobile_no": 1}],
				"links": [
					{
						"link_doctype": "Enterprise",
						"link_name": enterprise.name,
						"link_title": enterprise.enterprise_name,
					}
				],
			}
		).insert()
		address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": self.prefix,
				"address_type": "Office",
				"address_line1": "Enterprise Road",
				"city": "Nairobi",
				"links": [
					{
						"link_doctype": "Enterprise",
						"link_name": enterprise.name,
						"link_title": enterprise.enterprise_name,
					}
				],
			}
		).insert()

		enterprise.enterprise_primary_contact = contact.name
		enterprise.enterprise_primary_address = address.name
		enterprise.save()

		enterprise.reload()
		enterprise.run_method("onload")

		self.assertEqual(enterprise.enterprise_primary_contact, contact.name)
		self.assertEqual(enterprise.enterprise_primary_address, address.name)
		self.assertEqual(enterprise.get("__onload").contact_list[0].name, contact.name)
		self.assertEqual(enterprise.get("__onload").addr_list[0].name, address.name)
		self.assertEqual(
			get_enterprise_primary(
				"Contact",
				self.prefix,
				"name",
				0,
				20,
				{"enterprise": enterprise.name, "type": "Contact"},
			)[0][0],
			contact.name,
		)
		self.assertEqual(
			get_enterprise_primary(
				"Address",
				self.prefix,
				"name",
				0,
				20,
				{"enterprise": enterprise.name, "type": "Address"},
			)[0][0],
			address.name,
		)

	def test_enterprise_name_colliding_with_website_slug_is_rejected(self):
		frappe.get_doc(
			{"doctype": "Enterprise", "enterprise_name": f"{self.prefix} Acme"}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{"doctype": "Enterprise", "enterprise_name": f"{self.prefix}, Acme!"}
			).insert(ignore_permissions=True)
