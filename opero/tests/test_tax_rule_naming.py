from unittest.mock import patch

import frappe
from frappe.model.naming import set_new_name
from frappe.tests.utils import FrappeTestCase

from opero import hooks
from opero.events.tax_rule import autoname


class TestTaxRuleNaming(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.db.savepoint("tax_rule_naming")
		frappe.db.sql(
			"delete from `tabSeries` where name like %s",
			("TRL-%",),
		)

	def tearDown(self):
		frappe.db.rollback(save_point="tax_rule_naming")
		super().tearDown()

	def test_type_and_start_date_control_names(self):
		self.assertEqual(self._name("Purchase", "2026-04-02"), "TRL-P-0426")
		self.assertEqual(self._name("Sales", "2026-04-02"), "TRL-S-0426")
		self.assertEqual(self._name("Purchase", "2026-05-02"), "TRL-P-0526")
		self.assertEqual(self._name("Purchase", "2027-04-02"), "TRL-P-0427")

	def test_missing_start_date_is_explicit_even_with_an_end_date(self):
		self.assertEqual(self._name("Purchase", None, to_date="2026-04-30"), "TRL-P-UNDATED")
		self.assertEqual(self._name("Sales", ""), "TRL-S-UNDATED")

	def test_same_month_across_companies_uses_a_shared_counter(self):
		self.assertEqual(self._name("Purchase", "2026-04-02", company="First"), "TRL-P-0426")
		self.assertEqual(self._name("Purchase", "2026-04-30", company="Second"), "TRL-P-0426-02")
		self.assertEqual(self._name("Purchase", None), "TRL-P-UNDATED")
		self.assertEqual(self._name("Purchase", None), "TRL-P-UNDATED-02")

	def test_manually_named_records_are_not_reused(self):
		with patch.object(frappe.db, "exists", side_effect=[True, True, False]):
			self.assertEqual(self._name("Purchase", "2026-04-02"), "TRL-P-0426-03")

	def test_invalid_type_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self._name("", "2026-04-02")

	def test_hook_overrides_the_site_naming_expression(self):
		self.assertEqual(hooks.doc_events["Tax Rule"]["autoname"], "opero.events.tax_rule.autoname")
		doc = frappe.get_doc({"doctype": "Tax Rule", "tax_type": "Purchase", "from_date": "2026-04-02"})
		set_new_name(doc)
		self.assertEqual(doc.name, "TRL-P-0426")

	def _name(self, tax_type, from_date, **values):
		doc = frappe.get_doc({"doctype": "Tax Rule", "tax_type": tax_type, "from_date": from_date, **values})
		autoname(doc)
		return doc.name
