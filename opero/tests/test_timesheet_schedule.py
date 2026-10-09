from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.api.timesheet import preview_daily_times
from opero.events.timesheet import generate_daily_times


class TestTimesheetSchedule(FrappeTestCase):
	def test_seven_hour_row_survives_erpnext_hour_calculation(self):
		doc = frappe.get_doc(
			{
				"doctype": "Timesheet",
				"employee": "SCHEDULE-TEST",
				"time_logs": [
					{
						"task": "SCHEDULE-TASK",
						"description": "Delivery",
						"from_time": "2026-10-09 08:30:00",
						"hours": 7,
						"billing_hours": 7,
						"is_billable": 1,
					}
				],
			}
		)
		with (
			patch("opero.events.timesheet.frappe.db.sql", return_value=[]),
			patch(
				"opero.events.timesheet.frappe.db.get_single_value",
				side_effect=lambda dt, field: 7 if field == "standard_working_hours" else "08:30:00",
			),
		):
			generate_daily_times(doc)
			generate_daily_times(doc)
			get_doc = frappe.get_doc
			with patch(
				"opero.api.timesheet.frappe.get_doc",
				side_effect=lambda *args, **kwargs: MagicMock()
				if args[0] == "Employee"
				else get_doc(*args, **kwargs),
			):
				preview = preview_daily_times(
					"SCHEDULE-TEST",
					[{"name": "preview-row", "from_time": "2026-10-09 08:30:00", "hours": 7}],
				)
			self.assertEqual(preview[0]["name"], "preview-row")
			self.assertEqual(len(preview), 1)
			self.assertEqual(preview[0]["to_time"], "2026-10-09 15:30:00")
		doc.calculate_hours()
		self.assertEqual([row.hours for row in doc.time_logs], [7])
		self.assertEqual(sum(row.billing_hours for row in doc.time_logs), 7)
		self.assertTrue(all(row.task == "SCHEDULE-TASK" for row in doc.time_logs))
		self.assertTrue(all(row.description == "Delivery" for row in doc.time_logs))
		self.assertEqual([row.idx for row in doc.time_logs], [1])
		self.assertEqual(str(doc.time_logs[-1].to_time), "2026-10-09 15:30:00")

	def test_start_is_next_to_standard_working_hours(self):
		meta = frappe.get_meta("HR Settings")
		field = meta.get_field("custom_work_day_starts_at")
		self.assertEqual(field.default, "08:30:00")
		self.assertEqual(field.insert_after, "standard_working_hours")
		self.assertTrue(field.reqd)
