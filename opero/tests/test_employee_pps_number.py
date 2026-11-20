"""Employee PPS Number format and check character."""

from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase

from opero.opero_site.employee import is_valid_pps_number
from opero.tests.website_employee import clear_website_test_employees, make_website_employee


class TestEmployeePPSNumber(FrappeTestCase):
	def setUp(self):
		clear_website_test_employees()

	def test_check_character(self):
		self.assertTrue(is_valid_pps_number("1234567T"))
		self.assertTrue(is_valid_pps_number("1234567FA"))
		self.assertFalse(is_valid_pps_number("1234567A"))
		self.assertFalse(is_valid_pps_number("1234567FB"))
		self.assertFalse(is_valid_pps_number("123456T"))

	def test_number_is_stored_upper_case_without_spaces(self):
		doc = make_website_employee("PPS Holder", show_on_website=0, pps_number=" 1234567 fa ")
		self.assertEqual(doc.pps_number, "1234567FA")

	def test_invalid_number_is_rejected(self):
		with self.assertRaisesRegex(ValidationError, "is not valid"):
			make_website_employee("Bad PPS", show_on_website=0, pps_number="1234567FB")

	def test_number_is_optional(self):
		doc = make_website_employee("No PPS", show_on_website=0)
		self.assertIsNone(doc.pps_number)
