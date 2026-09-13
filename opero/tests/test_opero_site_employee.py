"""Employee website-team slug, status, and frontmatter contract."""

from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase

import frappe

from opero.opero_site.utils import slugify
from opero.tests.website_employee import clear_website_test_employees, make_website_employee


class TestEmployeeWebsiteTeam(FrappeTestCase):
	def test_alternative_image_defaults_off_and_can_be_toggled(self):
		doc = make_website_employee("Image Choice", image="/files/profile.jpg", portrait="/files/alternative.jpg")
		self.assertFalse(doc.use_alternative_image)
		self.assertEqual(doc.to_site_frontmatter()["image"], "/files/profile.jpg")
		doc.use_alternative_image = 1
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.to_site_frontmatter()["image"], "/files/alternative.jpg")
		doc.use_alternative_image = 0
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.to_site_frontmatter()["image"], "/files/profile.jpg")
		self.assertEqual(doc.portrait, "/files/alternative.jpg")

	def test_alternative_image_migration_preserves_existing_selection(self):
		from opero.patches.v0_4.use_alternative_personnel_image import execute

		doc = make_website_employee("Existing Alternative", image="/files/profile.jpg", portrait="/files/alternative.jpg", use_alternative_image=1)
		execute()
		doc.reload()
		self.assertTrue(doc.use_alternative_image)
		self.assertEqual(doc.image, "/files/profile.jpg")
		meta = frappe.get_meta("Employee")
		self.assertFalse(meta.has_field("use_employee_image"))
		self.assertEqual(meta.get_field("portrait").label, "Alternative image")
		self.assertEqual(meta.get_field("portrait").depends_on, "eval:doc.use_alternative_image")

	def test_personnel_type_and_series_layout_is_stable(self):
		from opero.patches.v0_4.swap_personnel_type_and_series import execute

		order = [field.fieldname for field in frappe.get_meta("Employee").fields]
		self.assertLess(order.index("custom_personnel_type"), order.index("naming_series"))
		self.assertLess(order.index("branch"), order.index("opero_website_tab"))
		execute()
		self.assertEqual(order, [field.fieldname for field in frappe.get_meta("Employee").fields])

	def setUp(self):
		clear_website_test_employees()

	def test_slugify_matches_content_filenames(self):
		self.assertEqual(slugify("Nicola Greene"), "nicola-greene")
		self.assertEqual(slugify("  Anita  Onyango "), "anita-onyango")

	def test_personnel_type_determines_new_employee_series(self):
		for personnel_type, prefix, wrong_series in (
			("Staff", "OSL_EMP_", "OSL_CON_.###"),
			("Consultant", "OSL_CON_", "OSL_EMP_.###"),
		):
			with self.subTest(personnel_type=personnel_type):
				doc = make_website_employee(
					f"New {personnel_type}",
					custom_personnel_type=personnel_type,
					naming_series=wrong_series,
				)
				self.assertEqual(doc.naming_series, f"{prefix}.###")
				self.assertRegex(doc.name, f"^{prefix}[0-9]{{3,}}$")

	def test_changing_existing_personnel_type_does_not_rename(self):
		doc = make_website_employee("Existing Staff", custom_personnel_type="Staff")
		name, series = doc.name, doc.naming_series
		doc.custom_personnel_type = "Consultant"
		doc.save(ignore_permissions=True)
		doc.reload()
		self.assertEqual(doc.name, name)
		self.assertEqual(doc.naming_series, series)

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
			use_alternative_image=0,
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
			"Custom Portrait", use_alternative_image=1, portrait="/files/custom.jpg"
		)
		self.assertEqual(doc.to_site_frontmatter()["image"], "/files/custom.jpg")
