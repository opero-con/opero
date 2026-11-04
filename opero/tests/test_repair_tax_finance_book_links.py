"""Exercise the partial-rename repair against real Frappe link tables."""

import unittest

import frappe

from opero.patches.v0_4.repair_tax_finance_book_links import execute


class TestRepairTaxFinanceBookLinks(unittest.TestCase):
	def setUp(self):
		frappe.db.savepoint("tax_finance_book_test")
		self.addCleanup(frappe.clear_cache)
		self.addCleanup(frappe.db.rollback, save_point="tax_finance_book_test")
		frappe.db.delete("Finance Book", {"name": ["in", ["Tax", "Statutory"]]})
		self.book = self.record("Finance Book", name="Tax", finance_book_name="Statutory")

	def record(self, doctype, **values):
		values.setdefault("name", "test-tax-" + frappe.generate_hash(length=10))
		doc = frappe.get_doc({"doctype": doctype, **values})
		# Reproduce a broken rename without invoking normal link validation.
		doc.db_insert()
		return doc

	def row(self, doc):
		return dict(frappe.db.get_value(doc.doctype, doc.name, "*", as_dict=True))

	def test_repairs_submitted_and_child_links_without_changing_other_fields(self):
		asset = self.record("Asset", docstatus=1, asset_name="Historical asset")
		docs = [
			self.record(
				"Asset Finance Book",
				parent=asset.name,
				parenttype="Asset",
				parentfield="finance_books",
				finance_book="Statutory",
				docstatus=1,
				depreciation_method="Straight Line",
				frequency_of_depreciation=12,
				total_number_of_depreciations=8,
			),
			self.record("Asset Category", asset_category_name="Repair test"),
			self.record("Journal Entry", finance_book="Statutory", docstatus=1, total_debit=123),
			self.record("GL Entry", finance_book="Statutory", docstatus=1, debit=123, credit=0),
			self.record(
				"Asset Depreciation Schedule", finance_book="Statutory", docstatus=1, asset=asset.name
			),
			self.record("Company", company_name="Repair test", default_finance_book="Statutory"),
		]
		category = docs[1]
		docs[1] = self.record(
			"Asset Finance Book",
			parent=category.name,
			parenttype="Asset Category",
			parentfield="finance_books",
			finance_book="Statutory",
			salvage_value_percentage=0,
		)
		before = {doc.name: self.row(doc) for doc in docs}
		other = self.record("GL Entry", finance_book="Accounting", debit=9)
		other_before = self.row(other)

		execute()

		for doc in docs:
			field = "default_finance_book" if doc.doctype == "Company" else "finance_book"
			self.assertEqual(self.row(doc), {**before[doc.name], field: "Tax"})
		self.assertEqual(self.row(other), other_before)
		self.assertEqual(frappe.db.get_value("Finance Book", "Tax", "finance_book_name"), "Tax")
		self.assertFalse(frappe.db.exists("Finance Book", "Statutory"))

	def test_second_execution_is_a_no_op(self):
		doc = self.record("Journal Entry", finance_book="Statutory", docstatus=1)
		execute()
		before = self.row(doc)
		execute()
		self.assertEqual(self.row(doc), before)
		self.assertEqual(before["finance_book"], "Tax")

	def test_preserves_two_legitimate_books(self):
		frappe.db.set_value("Finance Book", "Tax", "finance_book_name", "Tax")
		self.record("Finance Book", name="Statutory", finance_book_name="Statutory")
		doc = self.record("Journal Entry", finance_book="Statutory", docstatus=1)
		before = self.row(doc)
		execute()
		self.assertEqual(self.row(doc), before)

	def test_missing_tax_book_is_a_no_op(self):
		frappe.db.delete("Finance Book", {"name": "Tax"})
		doc = self.record("Journal Entry", finance_book="Statutory", docstatus=1)
		before = self.row(doc)
		execute()
		self.assertEqual(self.row(doc), before)

	def test_correctly_named_tax_book_does_not_trigger_a_repair(self):
		frappe.db.set_value("Finance Book", "Tax", "finance_book_name", "Tax")
		doc = self.record("Journal Entry", finance_book="Statutory", docstatus=1)
		before = self.row(doc)
		execute()
		self.assertEqual(self.row(doc), before)

	def test_repairs_dynamic_links_without_changing_other_fields(self):
		doc = self.record(
			"ToDo", reference_type="Finance Book", reference_name="Statutory", description="Review book"
		)
		before = self.row(doc)
		execute()
		self.assertEqual(self.row(doc), {**before, "reference_name": "Tax"})
