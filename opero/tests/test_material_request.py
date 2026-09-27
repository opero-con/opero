import json

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.patches.v0_4.show_material_request_item_rate import reset_saved_grid_columns


class TestMaterialRequestItemGrid(FrappeTestCase):
	def test_grid_shows_item_budget_line_quantity_uom_and_rate(self):
		meta = frappe.get_meta("Material Request Item")
		columns = [field.fieldname for field in meta.fields if field.in_list_view]
		self.assertEqual(columns, ["item_code", "custom_budget_line", "qty", "uom", "rate"])

	def test_reset_drops_only_saved_item_grid_columns(self):
		saved = {
			"GridView": {"Material Request Item": [{"fieldname": "qty"}], "Other": []},
			"last_view": "List",
		}
		frappe.db.sql(
			"insert into `__UserSettings` (`user`, `doctype`, `data`) values (%s, %s, %s)",
			("Guest", "Material Request", json.dumps(saved)),
		)

		reset_saved_grid_columns()

		data = frappe.db.sql(
			"select `data` from `__UserSettings` where `user`=%s and `doctype`=%s",
			("Guest", "Material Request"),
		)[0][0]
		self.assertEqual(json.loads(data), {"GridView": {"Other": []}, "last_view": "List"})


class TestMaterialRequestLayout(FrappeTestCase):
	def test_purpose_and_dates_share_the_first_row(self):
		fields = [field.fieldname for field in frappe.get_meta("Material Request").fields]
		first_section = fields[: fields.index("custom_request_details_section")]
		self.assertEqual(
			first_section,
			[
				"type_section",
				"material_request_type",
				"column_break_2",
				"transaction_date",
				"custom_required_by_column",
				"schedule_date",
			],
		)

	def test_company_price_list_and_target_warehouse_share_the_second_row(self):
		fields = [field.fieldname for field in frappe.get_meta("Material Request").fields]
		breaks = ["custom_request_details_section", "custom_request_details_column", "column_break5"]
		column_heads = [fields[fields.index(name) + 1] for name in breaks]
		self.assertEqual(column_heads, ["company", "buying_price_list", "set_warehouse"])
		self.assertEqual(fields[fields.index("set_warehouse") + 1], "warehouse_section")

