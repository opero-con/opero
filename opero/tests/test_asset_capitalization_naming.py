from datetime import datetime
from unittest.mock import patch

import frappe
from erpnext.assets.doctype.asset_capitalization.asset_capitalization import AssetCapitalization
from frappe.model.naming import set_new_name
from frappe.tests.utils import FrappeTestCase

from opero.patches.v0_4.set_asset_capitalization_naming_series import execute


class TestAssetCapitalizationNaming(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.db.savepoint("asset_capitalization_naming")
		frappe.db.sql(
			"delete from `tabSeries` where name in (%s, %s, %s)",
			("ASC-2607", "ASC-2608", "ASC-2707"),
		)

	def tearDown(self):
		frappe.db.rollback(save_point="asset_capitalization_naming")
		frappe.clear_cache(doctype="Asset Capitalization")
		super().tearDown()

	def test_posting_month_controls_the_sequence_instead_of_creation_month(self):
		with patch("frappe.model.naming.now_datetime", return_value=datetime(2026, 11, 4)):
			self.assertEqual(self._name("2026-07-04"), "ASC-26071")
			self.assertEqual(self._name("2026-08-01"), "ASC-26081")
			self.assertEqual(self._name("2026-07-31"), "ASC-26072")
			self.assertEqual(self._name("2027-07-01"), "ASC-27071")

	def test_existing_monthly_counter_is_reused_and_can_grow(self):
		frappe.db.sql("insert into `tabSeries` (name, current) values (%s, %s)", ("ASC-2607", 9))
		self.assertEqual(self._name("2026-07-04"), "ASC-260710")

	def test_migration_sets_the_displayed_series_without_resetting_counters(self):
		execute()
		self.assertEqual(self._name("2026-07-04"), "ASC-26071")
		execute()
		field = frappe.get_meta("Asset Capitalization").get_field("naming_series")
		self.assertEqual(field.options, "ASC-.YY.MM.#")
		self.assertEqual(field.default, "ASC-.YY.MM.#")
		self.assertEqual(self._name("2026-07-04"), "ASC-26072")

	def test_missing_posting_date_does_not_fall_back_to_today(self):
		with self.assertRaises(frappe.MandatoryError):
			self._name(None)

	def test_editing_a_saved_drafts_posting_date_keeps_its_name(self):
		# Isolate naming and persistence from stock valuation; no stock or GL is posted.
		with patch.object(AssetCapitalization, "validate"), patch.object(AssetCapitalization, "on_update"):
			doc = self._doc("2026-07-04")
			doc.insert(ignore_permissions=True, ignore_links=True, ignore_mandatory=True)
			name = doc.name
			doc.posting_date = "2026-08-01"
			doc.save(ignore_permissions=True)
			execute()
			self.assertEqual(doc.name, name)
			self.assertEqual(str(doc.reload().posting_date), "2026-08-01")

	def test_amendments_keep_frappes_suffix(self):
		with patch("frappe.model.naming.frappe.get_single_value", return_value="Amend Naming"):
			doc = self._doc("2026-08-01")
			doc.amended_from = "ASC-26071"
			set_new_name(doc)
			self.assertEqual(doc.name, "ASC-26071-1")

	def _name(self, posting_date):
		doc = self._doc(posting_date)
		set_new_name(doc)
		return doc.name

	def _doc(self, posting_date):
		return frappe.get_doc(
			{
				"doctype": "Asset Capitalization",
				"posting_date": posting_date,
				"naming_series": "ASC-.YY.MM.#",
			}
		)
