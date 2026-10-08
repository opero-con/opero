"""Daily retrospective scheduling regressions; no database writes."""

from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from opero.events.timesheet import generate_daily_times


class TestDailyTimes(TestCase):
	def setUp(self):
		self.doc = MagicMock()
		self.doc.docstatus = 0
		self.doc.employee = "EMP-1"
		self.doc.name = "TS-1"
		self.doc.get_doc_before_save.return_value = None
		self.doc.time_logs = [frappe._dict(idx=1, from_time="2026-09-30 21:54:32", hours=2.5)]
		self.frappe_patch = patch("opero.events.timesheet.frappe")
		self.frappe = self.frappe_patch.start()
		self.addCleanup(self.frappe_patch.stop)
		self.db = self.frappe.db
		self.db.get_single_value.return_value = 8
		self.db.sql.return_value = []

		def throw(message, **kwargs):
			raise ValueError(message)

		self.frappe.throw.side_effect = throw

	def test_late_entry_stays_on_selected_day(self):
		generate_daily_times(self.doc)
		self.assertEqual(self.doc.time_logs[0].from_time, datetime(2026, 9, 30, 8))
		self.assertEqual(self.doc.time_logs[0].to_time, datetime(2026, 9, 30, 10, 30))

	def test_skips_occupied_intervals_and_preserves_other_records(self):
		self.db.sql.return_value = [
			frappe._dict(from_time="2026-09-30 09:00:00", to_time="2026-09-30 11:00:00", hours=2)
		]
		generate_daily_times(self.doc)
		self.assertEqual(self.doc.time_logs[0].from_time, datetime(2026, 9, 30, 11))
		self.assertEqual(self.doc.time_logs[0].to_time, datetime(2026, 9, 30, 13, 30))

	def test_daily_total_across_other_timesheets(self):
		self.db.sql.return_value = [
			frappe._dict(from_time="2026-09-30 08:00:00", to_time="2026-09-30 14:00:00", hours=6)
		]
		with self.assertRaisesRegex(ValueError, "daily limit"):
			generate_daily_times(self.doc)

	def test_multiple_rows_share_daily_limit(self):
		self.doc.time_logs.append(frappe._dict(idx=2, from_time="2026-09-30 22:00:00", hours=6))
		with self.assertRaisesRegex(ValueError, "daily limit"):
			generate_daily_times(self.doc)

	def test_does_not_spill_when_day_is_full(self):
		self.db.sql.return_value = [
			frappe._dict(from_time="2026-09-30 09:00:00", to_time="2026-09-30 23:00:00", hours=14)
		]
		self.db.get_single_value.return_value = 24
		with self.assertRaisesRegex(ValueError, "cannot fit"):
			generate_daily_times(self.doc)

	def test_mixed_dates_blocked(self):
		self.doc.time_logs.append(frappe._dict(idx=2, from_time="2026-10-01 00:00:00", hours=0.5))
		with self.assertRaisesRegex(ValueError, "same work date"):
			generate_daily_times(self.doc)

	def test_missing_hr_limit_blocks(self):
		self.db.get_single_value.return_value = 0
		with self.assertRaisesRegex(ValueError, "HR Settings"):
			generate_daily_times(self.doc)

	def test_approved_record_unchanged(self):
		self.doc.get_doc_before_save.return_value = frappe._dict(docstatus=1)
		generate_daily_times(self.doc)
		self.assertEqual(self.doc.time_logs[0].from_time, "2026-09-30 21:54:32")
		self.db.sql.assert_not_called()

	def test_approval_runs_generator(self):
		self.doc.docstatus = 1
		self.doc.get_doc_before_save.return_value = frappe._dict(docstatus=0)
		generate_daily_times(self.doc)
		self.assertEqual(self.doc.time_logs[0].from_time, datetime(2026, 9, 30, 8))

	def test_rows_are_scheduled_consecutively(self):
		self.doc.time_logs.append(frappe._dict(idx=2, from_time="2026-09-30 23:00:00", hours=1))
		generate_daily_times(self.doc)
		self.assertEqual(self.doc.time_logs[1].from_time, datetime(2026, 9, 30, 10, 30))
		self.assertEqual(self.doc.time_logs[1].to_time, datetime(2026, 9, 30, 11, 30))

	def test_missing_personnel_blocks(self):
		self.doc.employee = None
		with self.assertRaisesRegex(ValueError, "Personnel"):
			generate_daily_times(self.doc)

	def test_zero_hours_blocks(self):
		self.doc.time_logs[0].hours = 0
		with self.assertRaisesRegex(ValueError, "greater than zero"):
			generate_daily_times(self.doc)

	def test_cancelled_document_is_not_rescheduled(self):
		self.doc.docstatus = 2
		generate_daily_times(self.doc)
		self.db.sql.assert_not_called()

	def test_exact_midnight_is_allowed(self):
		self.db.get_single_value.return_value = 16
		self.doc.time_logs[0].hours = 16
		generate_daily_times(self.doc)
		self.assertEqual(self.doc.time_logs[0].to_time, datetime(2026, 10, 1))
