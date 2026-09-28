# Copyright (c) 2026, Patrick Willy and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import date, timedelta

import frappe
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from frappe import _
from frappe.utils import add_months, cint, flt, getdate, today

from opero.opero.report.timesheet_permissions import match_conditions

LEAVE_DAYS = {"On Leave": 1, "Half Day": 0.5}


def execute(filters=None):
	report = WeeklyHours(frappe._dict(filters or {}))
	return report.columns, report.rows, report.message, report.chart


def get_week_start(day: date) -> date:
	return day - timedelta(days=day.weekday())


class WeeklyHours:
	"""Submitted timesheet hours per employee per Monday-start week, against expected hours."""

	def __init__(self, filters):
		self.to_date = getdate(filters.to_date or today())
		self.from_date = getdate(filters.from_date or add_months(self.to_date, -1))
		self.include_awaiting_approval = cint(filters.include_awaiting_approval)
		if self.from_date > self.to_date:
			frappe.throw(_("From Date must be on or before To Date"))
		self.standard_hours = flt(frappe.db.get_single_value("HR Settings", "standard_working_hours"))
		if not self.standard_hours:
			frappe.throw(_("Set Standard Working Hours in HR Settings to calculate expected hours"))
		first_week = get_week_start(self.from_date)
		week_count = (get_week_start(self.to_date) - first_week).days // 7 + 1
		self.weeks = [first_week + timedelta(weeks=index) for index in range(week_count)]

		employees = self.get_employees(filters)
		names = [employee.name for employee in employees]
		self.hours = self.get_hours(names)
		self.employees = [
			employee
			for employee in employees
			if any(self.is_employed(employee, day) for day in self.get_days_in_range())
			or any((employee.name, week) in self.hours for week in self.weeks)
		]
		self.leave = self.get_leave(names)
		self.calendars = self.get_calendars()

	def get_employees(self, filters):
		conditions = {"company": filters.company} if filters.company else {}
		if filters.employee:
			conditions["name"] = filters.employee
		return frappe.get_list(
			"Employee",
			filters=conditions,
			fields=[
				"name",
				"employee_name",
				"status",
				"employment_type",
				"date_of_joining",
				"relieving_date",
			],
			order_by="employee_name",
			limit_page_length=0,
		)

	def get_hours(self, employees):
		if not employees:
			return {}
		rows = frappe.db.sql(
			f"""
			SELECT ts.employee, DATE(tsd.from_time) AS day, SUM(tsd.hours) AS hours
			FROM `tabTimesheet Detail` tsd
			JOIN `tabTimesheet` ts ON ts.name = tsd.parent
			WHERE (ts.docstatus = 1 OR (%(include_awaiting_approval)s AND ts.docstatus = 0
			       AND ts.workflow_state = 'Submitted'))
			  AND ts.employee IN %(employees)s
			  AND tsd.from_time >= %(from_date)s AND tsd.from_time < %(until)s
			  {match_conditions("Timesheet", "ts")}
			GROUP BY ts.employee, DATE(tsd.from_time)
			""",
			{
				"employees": employees,
				"include_awaiting_approval": self.include_awaiting_approval,
				"from_date": self.from_date,
				"until": self.to_date + timedelta(days=1),
			},
			as_dict=True,
		)
		hours = {}
		for row in rows:
			key = (row.employee, get_week_start(getdate(row.day)))
			hours[key] = hours.get(key, 0) + flt(row.hours)
		return hours

	def get_leave(self, employees):
		if not employees:
			return {}
		rows = frappe.get_all(
			"Attendance",
			filters={
				"docstatus": 1,
				"employee": ["in", employees],
				"status": ["in", list(LEAVE_DAYS)],
				"attendance_date": ["between", [self.from_date, self.to_date]],
			},
			fields=["employee", "attendance_date", "status"],
		)
		return {(row.employee, getdate(row.attendance_date)): LEAVE_DAYS[row.status] for row in rows}

	def get_calendars(self):
		holiday_lists = {
			employee.name: get_holiday_list_for_employee(employee.name, raise_exception=False)
			for employee in self.employees
		}
		calendars = {}
		for name in set(filter(None, holiday_lists.values())):
			calendar = frappe.db.get_value("Holiday List", name, ["from_date", "to_date"], as_dict=True)
			calendar.holidays = set(
				frappe.get_all(
					"Holiday",
					filters={
						"parent": name,
						"parenttype": "Holiday List",
						"holiday_date": ["between", [self.from_date, self.to_date]],
					},
					pluck="holiday_date",
				)
			)
			calendars[name] = calendar
		return {employee: calendars.get(name) for employee, name in holiday_lists.items()}

	def get_days_in_range(self, week=None):
		start, end = (week, week + timedelta(days=6)) if week else (self.from_date, self.to_date)
		start, end = max(start, self.from_date), min(end, self.to_date)
		return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]

	def is_employed(self, employee, day):
		if employee.date_of_joining and day < getdate(employee.date_of_joining):
			return False
		if employee.relieving_date:
			return day <= getdate(employee.relieving_date)
		return employee.status == "Active"

	def get_expected_hours(self, employee, week):
		"""Working days less holidays and leave, times standard hours; None when unknown."""
		calendar = self.calendars.get(employee.name)
		if employee.employment_type == "Part-time" or not calendar:
			return None
		days = [day for day in self.get_days_in_range(week) if self.is_employed(employee, day)]
		if any(not calendar.from_date <= day <= calendar.to_date for day in days):
			return None
		working_days = [day for day in days if day not in calendar.holidays]
		leave = sum(self.leave.get((employee.name, day), 0) for day in working_days)
		return (len(working_days) - leave) * self.standard_hours

	@property
	def columns(self):
		columns = [{"fieldname": "personnel", "label": _("Personnel"), "fieldtype": "Data", "width": 200}]
		columns += [
			{
				"fieldname": get_week_key(week),
				"label": get_week_label(week),
				"fieldtype": "Float",
				"width": 90,
			}
			for week in self.weeks
		]
		return [
			*columns,
			{"fieldname": "total_hours", "label": _("Total"), "fieldtype": "Float", "width": 90},
			{"fieldname": "expected_hours", "label": _("Expected"), "fieldtype": "Float", "width": 90},
			{"fieldname": "difference", "label": _("Difference"), "fieldtype": "Float", "width": 100},
		]

	@property
	def rows(self):
		return [self.get_row(employee) for employee in self.employees]

	def get_row(self, employee):
		row = {"employee": employee.name, "personnel": employee.employee_name}
		expected = [self.get_expected_hours(employee, week) for week in self.weeks]
		for week, week_expected in zip(self.weeks, expected, strict=True):
			row[get_week_key(week)] = self.hours.get((employee.name, week), 0)
			row["expected_" + get_week_key(week)] = week_expected
		row["total_hours"] = sum(row[get_week_key(week)] for week in self.weeks)
		row["expected_hours"] = row["difference"] = None
		if None not in expected:
			row["expected_hours"] = sum(expected)
			row["difference"] = row["total_hours"] - row["expected_hours"]
		return row

	@property
	def message(self):
		unknown = [
			employee.employee_name
			for employee in self.employees
			if employee.employment_type != "Part-time"
			and None in (self.get_expected_hours(employee, week) for week in self.weeks)
		]
		timesheets = (
			_("Approved timesheets and those awaiting PM approval.")
			if self.include_awaiting_approval
			else _("Approved timesheets only.")
		)
		notes = [timesheets + " " + _("Part-time staff have no expected hours.")]
		if unknown:
			notes.append(_("No holiday list covers these dates for: {0}").format(", ".join(unknown)))
		return "<br>".join(notes)

	@property
	def chart(self):
		return {
			"data": {
				"labels": [get_week_label(week) for week in self.weeks],
				"datasets": [
					{
						"name": _("Hours"),
						"values": [
							sum(self.hours.get((employee.name, week), 0) for employee in self.employees)
							for week in self.weeks
						],
					}
				],
			},
			"type": "bar",
			"fieldtype": "Float",
		}


def get_week_key(week: date) -> str:
	return "week_" + week.strftime("%Y_%m_%d")


def get_week_label(week: date) -> str:
	"""ISO 8601 week then two-digit ISO year, such as W3926."""
	year, number, _ = week.isocalendar()
	return f"W{number:02d}{year % 100:02d}"
