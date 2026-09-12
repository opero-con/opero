"""Employee website-team slug, status, and frontmatter contract."""

from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase

from opero.opero_site.utils import slugify
from opero.tests.website_employee import clear_website_test_employees, make_website_employee


class TestEmployeeWebsiteTeam(FrappeTestCase):
	def setUp(self):
		clear_website_test_employees()

	def test_slugify_matches_content_filenames(self):
		self.assertEqual(slugify("Nicola Greene"), "nicola-greene")
		self.assertEqual(slugify("  Anita  Onyango "), "anita-onyango")

	def test_slug_is_generated_from_employee_name(self):
		doc = make_website_employee("Nicola Greene")
		self.assertEqual(doc.slug, "nicola-greene")

	def test_employee_hr_status_is_not_publish_status(self):
		doc = make_website_employee("New Draft", show_on_website=0)
		self.assertEqual(doc.status, "Active")
		self.assertEqual(doc.website_status, "Draft")
		self.assertFalse(doc.show_on_website)

	def test_published_employee_is_active_on_site(self):
		doc = make_website_employee("Published Member")
		doc.db_set("website_status", "Published")
		doc.reload()
		self.assertTrue(doc.to_site_frontmatter()["active"])

	def test_linkedin_must_be_full_url(self):
		with self.assertRaises(ValidationError):
			make_website_employee("Bad LinkedIn", linkedin="linkedin.com/in/example")

	def test_frontmatter_uses_employee_identity_and_image(self):
		doc = make_website_employee(
			"Anita Onyango",
			role="Director",
			linkedin="https://www.linkedin.com/in/anita-onyango",
			image="/files/anita.jpg",
			use_employee_image=1,
		)
		self.assertEqual(
			doc.to_site_frontmatter(),
			{
				"name": "Anita Onyango",
				"role": "Director",
				"image": "/files/anita.jpg",
				"imageAlt": "Portrait of Anita Onyango",
				"order": 10,
				"active": True,
				"linkedin": "https://www.linkedin.com/in/anita-onyango",
			},
		)

	def test_frontmatter_can_use_separate_portrait(self):
		doc = make_website_employee(
			"Custom Portrait", use_employee_image=0, portrait="/files/custom.jpg"
		)
		self.assertEqual(doc.to_site_frontmatter()["image"], "/files/custom.jpg")
