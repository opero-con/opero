"""Reset obsolete timesheet grid selections without losing other preferences."""

import json
from unittest import TestCase
from unittest.mock import patch

import frappe

from opero.patches.v0_4 import reset_timesheet_saved_grid_columns as migration


class TestTimesheetGridColumns(TestCase):
	def test_reset_all_users_preserves_other_preferences(self):
		settings = {
			"GridView": {
				"Timesheet Detail": [{"fieldname": "custom_a_hrs", "columns": 2}],
				"Other Detail": [{"fieldname": "description", "columns": 10}],
			},
			"List": {"filters": [["status", "=", "Draft"]]},
		}
		rows = [frappe._dict(user=user, data=json.dumps(settings)) for user in ("first", "second")]
		rows.append(frappe._dict(user="no-selection", data='{"List": {}}'))
		with (
			patch.object(migration, "frappe") as api,
			patch.object(migration, "sync_user_settings") as sync,
		):
			api.db.sql.return_value = rows
			migration.execute()
			sync.assert_called_once_with()
			api.cache.delete_value.assert_called_with("_user_settings")
			updates = [call for call in api.db.sql.call_args_list if call.args[0].startswith("update")]
			self.assertEqual(len(updates), 2)
			for call, user in zip(updates, ("first", "second"), strict=True):
				data, saved_user, doctype = call.args[1]
				self.assertEqual((saved_user, doctype), (user, "Timesheet"))
				expected = json.loads(json.dumps(settings))
				del expected["GridView"]["Timesheet Detail"]
				self.assertEqual(json.loads(data), expected)
