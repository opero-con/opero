"""Work Hours Summary — holidays/leave/available hours (ported from FC Server Script)."""

from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


MONTH_INDEX = {
	"January": 1,
	"February": 2,
	"March": 3,
	"April": 4,
	"May": 5,
	"June": 6,
	"July": 7,
	"August": 8,
	"September": 9,
	"October": 10,
	"November": 11,
	"December": 12,
}


class WorkHoursSummary(Document):
	def validate(self):
		self._populate_distribution_from_holidays()

	def _calendar_year(self) -> int | None:
		if not self.year:
			return None
		start = frappe.db.get_value("Fiscal Year", self.year, "year_start_date")
		if start:
			return getdate(start).year
		# Fallback: leading 4-digit year in the Fiscal Year name
		digits = "".join(ch for ch in str(self.year) if ch.isdigit())
		return int(digits[:4]) if len(digits) >= 4 else None

	def _populate_distribution_from_holidays(self):
		if not (self.holiday_list and self.year and self.personnel):
			return

		calendar_year = self._calendar_year()
		if not calendar_year:
			frappe.throw(f"Unable to resolve calendar year from Fiscal Year {self.year}")

		standard_working_hours = (
			frappe.db.get_single_value("HR Settings", "standard_working_hours") or 0
		)
		self.working_hours = standard_working_hours

		for row in self.distribution_detail or []:
			if not row.month or row.days is None:
				continue
			month_index = MONTH_INDEX.get(row.month)
			if not month_index:
				continue

			holidays_in_month = self._holidays_for_month(
				self.holiday_list, calendar_year, month_index
			)
			leave_days = self._leave_days(self.personnel, calendar_year, month_index)

			row.holidays = holidays_in_month
			row.leave = leave_days
			available_days = float(row.days or 0) - (holidays_in_month + leave_days)
			row.available_days = available_days
			row.standard_working_hours = standard_working_hours
			row.available_hours = available_days * float(standard_working_hours)

	@staticmethod
	def _holidays_for_month(holiday_list: str, year: int, month: int) -> int:
		try:
			count = frappe.db.sql(
				"""
				SELECT COUNT(*)
				FROM `tabHoliday`
				WHERE parent = %s
				  AND MONTH(holiday_date) = %s
				  AND YEAR(holiday_date) = %s
				""",
				(holiday_list, month, year),
			)
			return int(count[0][0] if count else 0)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Work Hours Summary holidays fetch")
			return 0

	@staticmethod
	def _leave_days(employee: str, year: int, month: int) -> int:
		try:
			count = frappe.db.sql(
				"""
				SELECT COUNT(*)
				FROM `tabAttendance`
				WHERE employee = %s
				  AND MONTH(attendance_date) = %s
				  AND YEAR(attendance_date) = %s
				  AND status = 'On Leave'
				  AND docstatus = 1
				""",
				(employee, month, year),
			)
			return int(count[0][0] if count else 0)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Work Hours Summary leave days")
			return 0
