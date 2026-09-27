import json

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.events.material_request import validate_material_request
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


class TestMaterialRequestTotal(FrappeTestCase):
	def test_total_sits_right_aligned_below_the_items_table(self):
		fields = [field.fieldname for field in frappe.get_meta("Material Request").fields]
		below_items = fields[fields.index("items") + 1 : fields.index("custom_total") + 1]
		self.assertEqual(
			below_items,
			[
				"custom_total_section",
				"custom_total_left_column",
				"custom_total_right_column",
				"custom_total",
			],
		)

	def test_total_sums_quantity_times_rate(self):
		request = frappe.get_doc(
			{
				"doctype": "Material Request",
				"items": [{"qty": 2, "rate": 10.5}, {"qty": 3, "rate": 4}, {"qty": 1}],
			}
		)

		validate_material_request(request)

		self.assertEqual(request.custom_total, 33)
