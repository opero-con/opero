"""Website contact form ingest: Communication with Source = Website."""

import frappe
from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase
from frappe.utils import escape_html

from opero.opero_site.enquiry import create_website_enquiry


class TestWebsiteEnquiry(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Communication", {"custom_source": "Website"})

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_communication_has_source_field(self):
		field = frappe.get_meta("Communication").get_field("custom_source")
		self.assertEqual(field.label, "Source")
		self.assertEqual(field.fieldtype, "Select")
		self.assertIn("Website", field.options.split("\n"))

	def test_create_website_enquiry_stores_a_communication(self):
		result = create_website_enquiry(
			full_name="Jane Doe",
			email="jane@example.org",
			subject="Training",
			message="Hello Opero",
			organization="Nairobi Water",
			consent="yes",
		)
		doc = frappe.get_doc("Communication", result["name"])
		self.assertEqual(doc.custom_source, "Website")
		self.assertEqual(doc.subject, "Training")
		self.assertEqual(doc.sender, "jane@example.org")
		self.assertEqual(doc.sender_full_name, "Jane Doe")
		self.assertEqual(doc.sent_or_received, "Received")
		self.assertEqual(doc.status, "Open")
		self.assertEqual(doc.communication_medium, "Other")
		self.assertIn("Nairobi Water", doc.text_content)
		self.assertIn("Hello Opero", doc.text_content)

	def test_create_website_enquiry_escapes_html(self):
		payload = '<script>alert("x")</script>'
		result = create_website_enquiry(
			full_name=payload,
			email="jane@example.org",
			subject="Other",
			message=payload,
			consent="yes",
		)
		doc = frappe.get_doc("Communication", result["name"])
		self.assertNotIn("<script>", doc.content)
		self.assertIn(escape_html(payload), doc.content)

	def test_create_website_enquiry_rejects_guest(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			create_website_enquiry(
				full_name="Jane Doe",
				email="jane@example.org",
				subject="Training",
				message="Hello Opero",
				consent="yes",
			)

	def test_create_website_enquiry_requires_consent_and_valid_email(self):
		with self.assertRaises(ValidationError):
			create_website_enquiry(
				full_name="Jane Doe",
				email="jane@example.org",
				subject="Training",
				message="Hello Opero",
				consent="no",
			)
		with self.assertRaises(ValidationError):
			create_website_enquiry(
				full_name="Jane Doe",
				email="not-an-email",
				subject="Training",
				message="Hello Opero",
				consent="yes",
			)
