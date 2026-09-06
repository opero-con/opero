"""Regression: Cubenet migrate died on legacy Home Page hero Singles fields."""

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.patches.v0_4.move_home_hero_image_into_table import _legacy_single, execute


class TestMoveHomeHeroImagePatch(FrappeTestCase):
	def test_execute_when_hero_image_field_already_removed(self):
		self.assertIsNone(frappe.get_meta("Home Page").get_field("hero_image"))
		with self.assertRaises(frappe.ValidationError):
			frappe.db.get_single_value("Home Page", "hero_image")
		execute()

	def test_legacy_single_reads_tab_singles_without_meta(self):
		frappe.db.sql(
			"""
			DELETE FROM tabSingles
			WHERE doctype = %s AND field = %s
			""",
			("Home Page", "hero_image"),
		)
		frappe.db.sql(
			"""
			INSERT INTO tabSingles (doctype, field, value)
			VALUES (%s, %s, %s)
			""",
			("Home Page", "hero_image", "/files/legacy-hero.jpg"),
		)
		self.assertEqual(_legacy_single("hero_image"), "/files/legacy-hero.jpg")
		frappe.db.sql(
			"""
			DELETE FROM tabSingles
			WHERE doctype = %s AND field = %s
			""",
			("Home Page", "hero_image"),
		)
