"""Weekly Hours report: submitted hours per week against expected hours."""

import unittest
from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.opero.report.weekly_hours import weekly_hours
from opero.opero.report.weekly_hours.weekly_hours import WeeklyHours

read_leave = WeeklyHours.get_leave
HOLIDAYS = (
	"2026-08-29",
	"2026-08-30",
	"2026-09-05",
	"2026-09-06",
	"2026-09-09",
	"2026-09-12",
	"2026-09-13",
	"2026-09-19",
	"2026-09-20",
)


class TestWeeklyHours(FrappeTestCase):
	def setUp(self):
		self.previous_user = frappe.session.user
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, self.previous_user)
		suffix = frappe.generate_hash(length=8)
		self.company = self._record("Company", company_name="Weekly hours " + suffix, abbr=suffix)
		self.holiday_list = self._record("Holiday List", from_date="2026-01-01", to_date="2026-12-31")
		for day in HOLIDAYS:
			self._child("Holiday", self.holiday_list, "Holiday List", "holidays", holiday_date=day)
		self.full_time = self._employee("Full Time", employment_type="Full-time")
		self.part_time = self._employee("Part Time", employment_type="Part-time")
		self.leave = {(self.full_time, date(2026, 9, 10)): 0.5}
		settings = patch.object(weekly_hours.frappe.db, "get_single_value", return_value=7)
		leave = patch.object(WeeklyHours, "get_leave", lambda report, employees: self.leave)
		settings.start()
		leave.start()
		self.addCleanup(settings.stop)
		self.addCleanup(leave.stop)

	def _record(self, doctype, **values):
		doc = frappe.get_doc(
			dict(doctype=doctype, name="wh-test-" + frappe.generate_hash(length=12), **values)
		)
		doc.db_insert()
		return doc.name

	def _child(self, doctype, parent, parenttype, parentfield, **values):
		return self._record(doctype, parent=parent, parenttype=parenttype, parentfield=parentfield, **values)

	def _employee(self, employee_name, **values):
		values = {
			"status": "Active",
			"date_of_joining": "2020-01-01",
			"holiday_list": self.holiday_list,
			**values,
		}
		return self._record(
			"Employee", employee_name=employee_name, first_name=employee_name, company=self.company, **values
		)

	def _sheet(self, employee, status, day, hours, workflow_state=None):
		name = self._record(
			"Timesheet", employee=employee, docstatus=status, start_date=day, workflow_state=workflow_state
		)
		self._child(
			"Timesheet Detail", name, "Timesheet", "time_logs", from_time=day + " 09:00:00", hours=hours
		)

	def _report(self, from_date="2026-09-07", to_date="2026-09-20", **filters):
		columns, data, message, chart = weekly_hours.execute(
			{"company": self.company, "from_date": from_date, "to_date": to_date, **filters}
		)
		return columns, {row["employee"]: row for row in data}, message, chart

	def test_weeks_count_submitted_hours_against_expected(self):
		self._sheet(self.full_time, 1, "2026-09-08", 7)
		self._sheet(self.full_time, 1, "2026-09-15", 30)
		self._sheet(self.full_time, 0, "2026-09-16", 100)
		self._sheet(self.full_time, 2, "2026-09-17", 100)
		columns, rows, _, chart = self._report()
		weeks = [column["fieldname"] for column in columns if column["fieldname"].startswith("week_")]
		self.assertEqual(weeks, ["week_2026_09_07", "week_2026_09_14"])
		self.assertEqual(columns[0]["fieldname"], "personnel")
		self.assertNotIn("employee", [column["fieldname"] for column in columns])
		self.assertEqual(rows[self.full_time]["personnel"], "Full Time")
		row = rows[self.full_time]
		self.assertEqual((row["week_2026_09_07"], row["week_2026_09_14"]), (7, 30))
		# Week one: five weekdays, a Wednesday holiday and a half day of leave.
		self.assertEqual((row["expected_week_2026_09_07"], row["expected_week_2026_09_14"]), (24.5, 35))
		self.assertEqual((row["total_hours"], row["expected_hours"], row["difference"]), (37, 59.5, -22.5))
		self.assertEqual(chart["data"]["datasets"][0]["values"], [7, 30])

	def test_awaiting_approval_is_included_only_when_ticked(self):
		self._sheet(self.full_time, 1, "2026-09-08", 7, "Approved")
		self._sheet(self.full_time, 0, "2026-09-09", 5, "Submitted")
		self._sheet(self.full_time, 0, "2026-09-10", 100, "Draft")
		self._sheet(self.full_time, 2, "2026-09-11", 100, "Cancelled")
		_, rows, message, _ = self._report()
		self.assertEqual(rows[self.full_time]["week_2026_09_07"], 7)
		self.assertTrue(message.startswith("Approved timesheets only."))
		_, rows, message, chart = self._report(include_awaiting_approval=1)
		self.assertEqual(rows[self.full_time]["week_2026_09_07"], 12)
		self.assertEqual(chart["data"]["datasets"][0]["values"][0], 12)
		self.assertTrue(message.startswith("Approved timesheets and those awaiting PM approval."))

	@unittest.skipUnless(
		frappe.get_meta("Employee").has_field("employment_type"), "Employment type needs HRMS"
	)
	def test_part_time_staff_have_hours_but_no_expected(self):
		self._sheet(self.part_time, 1, "2026-09-15", 10)
		_, rows, message, _ = self._report()
		row = rows[self.part_time]
		self.assertEqual(row["total_hours"], 10)
		self.assertIsNone(row["expected_week_2026_09_14"])
		self.assertIsNone(row["expected_hours"])
		self.assertNotIn("Part Time", message.split("<br>", 1)[-1])

	def test_partial_range_counts_only_days_inside_it(self):
		_, rows, _, _ = self._report(from_date="2026-09-09", to_date="2026-09-15")
		row = rows[self.full_time]
		# Wednesday is a holiday, Thursday a half day and Friday a full day; then Monday and Tuesday.
		self.assertEqual((row["expected_week_2026_09_07"], row["expected_week_2026_09_14"]), (10.5, 14))

	def test_expected_starts_at_joining_and_skips_employees_outside_range(self):
		joiner = self._employee("Joiner", date_of_joining="2026-09-16")
		leaver = self._employee("Leaver", status="Left", relieving_date="2026-08-31")
		_, rows, _, _ = self._report()
		self.assertEqual(
			(rows[joiner]["expected_week_2026_09_07"], rows[joiner]["expected_week_2026_09_14"]), (0, 21)
		)
		self.assertNotIn(leaver, rows)

	def test_missing_or_uncovered_holiday_list_is_flagged(self):
		no_list = self._employee("No List", holiday_list=None)
		short_list = self._record("Holiday List", from_date="2026-09-10", to_date="2026-12-31")
		for day in ("2026-09-19", "2026-09-20"):
			self._child("Holiday", short_list, "Holiday List", "holidays", holiday_date=day)
		uncovered = self._employee("Uncovered", holiday_list=short_list)
		_, rows, message, _ = self._report()
		self.assertIsNone(rows[no_list]["expected_hours"])
		self.assertIsNone(rows[no_list]["difference"])
		self.assertIsNone(rows[uncovered]["expected_week_2026_09_07"])
		self.assertEqual(rows[uncovered]["expected_week_2026_09_14"], 35)
		self.assertIn("No List", message)
		self.assertIn("Uncovered", message)
		self.assertNotIn("Full Time", message)

	def test_dates_default_to_the_month_up_to_today(self):
		with patch.object(weekly_hours, "today", return_value="2026-09-29"):
			columns, data, _, _ = weekly_hours.execute({"company": self.company})
		weeks = [column["fieldname"] for column in columns if column["fieldname"].startswith("week_")]
		self.assertEqual((weeks[0], weeks[-1]), ("week_2026_08_24", "week_2026_09_28"))
		row = next(row for row in data if row["employee"] == self.full_time)
		# Saturday 29 August to Tuesday 29 September: the first week has no weekdays in range.
		self.assertEqual((row["expected_week_2026_08_24"], row["expected_week_2026_09_28"]), (0, 14))

	def test_weeks_are_labelled_by_iso_week(self):
		# Sunday 1 January 2023 closes 2022-W52; 2023-W01 starts on Monday 2 January.
		self._sheet(self.full_time, 1, "2023-01-01", 3)
		self._sheet(self.full_time, 1, "2023-01-02", 4)
		columns, rows, _, chart = self._report(from_date="2022-12-26", to_date="2023-01-08")
		labels = {column["fieldname"]: column["label"] for column in columns}
		self.assertEqual(labels["week_2022_12_26"], "W5222")
		self.assertEqual(labels["week_2023_01_02"], "W0123")
		self.assertEqual(chart["data"]["labels"], ["W5222", "W0123"])
		row = rows[self.full_time]
		self.assertEqual((row["week_2022_12_26"], row["week_2023_01_02"]), (3, 4))

	def test_employee_filter_and_date_order(self):
		_, rows, _, _ = self._report(employee=self.part_time)
		self.assertEqual(set(rows), {self.part_time})
		with self.assertRaises(frappe.ValidationError):
			self._report(from_date="2026-09-21", to_date="2026-09-20")

	@unittest.skipUnless(frappe.db.exists("DocType", "Attendance"), "Attendance needs HRMS")
	def test_leave_reads_submitted_attendance(self):
		for status, day, docstatus in (
			("On Leave", "2026-09-14", 1),
			("Half Day", "2026-09-15", 1),
			("On Leave", "2026-09-16", 0),
		):
			self._record(
				"Attendance", employee=self.full_time, status=status, attendance_date=day, docstatus=docstatus
			)
		report = WeeklyHours.__new__(WeeklyHours)
		report.from_date, report.to_date = date(2026, 9, 7), date(2026, 9, 20)
		self.assertEqual(
			read_leave(report, [self.full_time]),
			{(self.full_time, date(2026, 9, 14)): 1, (self.full_time, date(2026, 9, 15)): 0.5},
		)

	def test_report_is_linked_from_the_opero_time_card(self):
		self.assertEqual(frappe.db.get_value("Report", "Weekly Hours", "report_type"), "Script Report")
		links = frappe.get_doc("Workspace", "Opero").links
		labels = [link.link_to for link in links if link.link_type == "Report"]
		self.assertIn("Weekly Hours", labels)
