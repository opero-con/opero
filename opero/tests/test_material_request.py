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

