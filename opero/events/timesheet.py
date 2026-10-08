"""Timesheet validators ported from FC Server Scripts."""

from __future__ import annotations

from datetime import timedelta
from math import isfinite

import frappe
from frappe.utils import add_to_date, escape_html, get_datetime, get_first_day, getdate, nowdate

SUBMISSION_CUTOFF_DAY = 3
SUBMISSION_CUTOFF_BYPASS_ROLES = {"Projects Manager"}


def validate_timesheet(doc, _method=None):
	_set_week_of_month(doc)
	_anti_spill(doc)
	_validate_allocated_hours(doc)


def generate_daily_times(doc, _method=None):
	"""Place retrospective hours in free intervals from 08:00 on the selected date."""
	previous = doc.get_doc_before_save()
	if doc.docstatus == 2 or (previous and previous.docstatus == 1):
		return
	rows = list(doc.time_logs or [])
	if not rows:
		return
	if not doc.employee:
		frappe.throw("Select Personnel before recording working hours.")
	if any(not row.from_time for row in rows):
		frappe.throw("Select a work date in From Time for every entry.")
	dates = {getdate(row.from_time) for row in rows}
	if len(dates) != 1:
		frappe.throw("All entries must use the same work date. Use a separate timesheet for another day.")
	day = get_datetime(next(iter(dates)))
	limit = float(frappe.db.get_single_value("HR Settings", "standard_working_hours") or 0)
	if not isfinite(limit) or limit <= 0:
		frappe.throw("Set a positive Standard Working Hours value in HR Settings.")
	for row in rows:
		hours = float(row.hours or 0)
		if not isfinite(hours) or hours <= 0:
			frappe.throw(f"Row {row.idx}: Hours must be greater than zero.")
	# Serialize all of this employee's saves, including drafts, before reading reservations.
	frappe.db.sql("SELECT name FROM `tabEmployee` WHERE name = %s FOR UPDATE", (doc.employee,))
	end = day + timedelta(days=1)
	occupied = frappe.db.sql(
		"""
		SELECT tl.from_time, tl.to_time, tl.hours
		FROM `tabTimesheet` ts JOIN `tabTimesheet Detail` tl ON tl.parent = ts.name
		WHERE ts.employee = %(employee)s AND ts.docstatus < 2 AND ts.name != %(name)s
		  AND tl.from_time < %(end)s AND tl.to_time > %(start)s
		ORDER BY tl.from_time FOR UPDATE
		""",
		{"employee": doc.employee, "name": doc.name or "", "start": day, "end": end},
		as_dict=True,
	)
	used = sum(
		(
			max(
				min(get_datetime(r.to_time), end) - max(get_datetime(r.from_time), day), timedelta()
			).total_seconds()
			/ 3600
		)
		for r in occupied
	)
	requested = sum(float(row.hours) for row in rows)
	if used + requested > limit + 0.000001:
		frappe.throw(
			f"{day.date()}: {used + requested:g}h total exceeds the {limit:g}h daily limit.",
			title="Daily limit exceeded",
		)
	intervals = [(get_datetime(r.from_time), get_datetime(r.to_time)) for r in occupied]
	cursor = day + timedelta(hours=8)
	for row in rows:
		duration = timedelta(seconds=round(float(row.hours) * 3600))
		if duration <= timedelta():
			frappe.throw(f"Row {row.idx}: Hours must represent at least one second.")
		for start, finish in intervals:
			if finish <= cursor:
				continue
			if cursor + duration <= start:
				break
			cursor = max(cursor, finish)
		if cursor + duration > end:
			frappe.throw(
				"These hours cannot fit after 08:00 on the selected date. Correct the hours or work date."
			)
		row.from_time = cursor
		row.to_time = cursor + duration
		cursor = row.to_time


def week_of_month(from_time):
	"""Monday-Sunday weeks, with the partial week containing the 1st as Week 1."""
	if not from_time:
		return ""
	date = get_datetime(from_time)
	week = (date.day - 1 + date.replace(day=1).weekday()) // 7 + 1
	return f"Week {week}"


def _set_week_of_month(doc):
	for row in doc.time_logs or []:
		row.custom_week_of_month = week_of_month(row.from_time)


def before_submit_timesheet(doc, _method=None):
	_validate_project_rate_factor(doc)
	_validate_submission_cutoff(doc)


def _safe_html(value) -> str:
	try:
		return escape_html(str(value or ""))
	except Exception:
		text = str(value or "")
		return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _pm_name_from_parent_project(parent_project: str | None) -> str | None:
	if not parent_project:
		return None
	emp_id = frappe.db.get_value("Project", parent_project, "custom_project_manager")
	if not emp_id:
		return None
	return frappe.db.get_value("Employee", emp_id, "employee_name")


def _anti_spill(doc):
	for row in doc.time_logs or []:
		ft = row.from_time
		hrs = row.hours
		if not ft or not hrs or hrs <= 0:
			continue

		if isinstance(ft, str):
			ft = get_datetime(ft)

		intended_seconds = int(hrs * 3600)
		end_dt = add_to_date(ft, seconds=intended_seconds)
		if ft.date() == end_dt.date():
			continue

		# An entry ending exactly at midnight belongs to the preceding day.
		if end_dt.time().isoformat() == "00:00:00" and (end_dt.date() - ft.date()).days == 1:
			continue
		frappe.throw(
			f"Row {row.idx}: this entry crosses midnight. Correct the hours or work date.",
			title="Entry exceeds work date",
		)


def _validate_allocated_hours(doc):
	rows = [row for row in (doc.time_logs or []) if doc.employee and row.task and row.from_time]
	if not rows:
		return
	# Serialize an employee's saves so concurrent submissions cannot spend the same balance.
	frappe.db.sql("SELECT name FROM `tabEmployee` WHERE name = %s FOR UPDATE", (doc.employee,))
	allocation, usage = get_monthly_balances(doc.employee, rows, doc.name, lock=True)
	current = {}
	for row in rows:
		key = (row.task, get_datetime(row.from_time).strftime("%b %Y"))
		current[key] = current.get(key, 0) + float(row.hours or 0)
		if hasattr(row, "custom_a_hrs"):
			row.custom_a_hrs = allocation.get(key, 0)
	pm = _safe_html(_pm_name_from_parent_project(doc.parent_project) or "PM")
	for (task, month), hours in current.items():
		budget = allocation.get((task, month), 0)
		posted = usage.get((task, month), 0)
		if budget <= 0 or posted + hours > budget + 0.000001:
			task_name = frappe.db.get_value("Task", task, "subject") or task
			frappe.throw(
				f"Task <b>{_safe_html(task_name)}</b>, {_safe_html(month)}: allocated {budget:g}h, "
				f"submitted {posted:g}h, this timesheet {hours:g}h. "
				f"Please contact the PM, <b>{pm}</b>, for review.",
				title="Exceeds monthly allocation" if budget > 0 else "No monthly allocation",
			)


def _validate_project_rate_factor(doc):
	project = doc.parent_project or ""
	project_name = project
	if project:
		project_name = frappe.db.get_value("Project", project, "project_name") or project
	project_name = _safe_html(project_name)

	allowed = (
		set(frappe.get_all("Activity Type", filters={"custom_project": project}, pluck="name"))
		if project
		else set()
	)
	invalid = [
		str(row.idx)
		for row in (doc.time_logs or [])
		if row.activity_type and row.activity_type not in allowed
	]
	if invalid:
		frappe.throw(
			f"Row(s) {', '.join(invalid)}: Project Rate Factor must belong to project {project_name}."
		)
	missing_rows = [str(row.idx or "") for row in (doc.time_logs or []) if not (row.activity_type or "")]
	if not missing_rows:
		return

	has_any = bool(allowed)
	if has_any:
		detail = f"Please pick a Project Rate Factor tied to project <b>{project_name}</b> or set a default."
	else:
		detail = (
			f"No Project Rate Factors are defined for project <b>{project_name}</b>. "
			"Please create one under the project."
		)
	frappe.throw(
		f"Row(s) {', '.join(missing_rows)}: Project Rate Factor is missing.<br>{detail}",
		title="Missing Project Rate Factor",
	)


def _validate_submission_cutoff(doc):
	if SUBMISSION_CUTOFF_BYPASS_ROLES & set(frappe.get_roles()):
		return
	months = {get_first_day(row.from_time) for row in (doc.time_logs or []) if row.from_time}
	if not months:
		return
	today = getdate(nowdate())
	for month_start in sorted(months):
		cutoff = get_first_day(month_start, d_months=1) + timedelta(days=SUBMISSION_CUTOFF_DAY - 1)
		if today > cutoff:
			frappe.throw(
				f"Timesheet entries for <b>{month_start.strftime('%B %Y')}</b> were due by "
				f"<b>{cutoff.strftime('%d %b %Y')}</b>. Please contact your project manager to submit "
				"after the cutoff.",
				title="Submission cutoff passed",
			)


def get_monthly_balances(employee, rows, name=None, lock=False):
	tasks = sorted({row.task for row in rows})
	allocated = frappe.db.sql(
		"""
		SELECT task, CONCAT(month, ' ', year) AS month, SUM(hours) AS hours
		FROM `tabTask Allocation`
		WHERE docstatus = 1 AND employee = %(employee)s AND task IN %(tasks)s
		GROUP BY task, month, year
		""",
		{"employee": employee, "tasks": tasks},
		as_dict=True,
	)
	allocation = {(r.task, r.month): float(r.hours or 0) for r in allocated}
	dates = [get_datetime(row.from_time) for row in rows]
	start = min(dates).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
	end = add_to_date(max(dates).replace(day=1, hour=0, minute=0, second=0, microsecond=0), months=1)
	used = frappe.db.sql(
		"""
		SELECT tl.task, DATE_FORMAT(tl.from_time, '%%b %%Y') AS month, SUM(tl.hours) AS hours
		FROM `tabTimesheet` ts JOIN `tabTimesheet Detail` tl ON tl.parent = ts.name
		WHERE ts.employee = %(employee)s AND ts.docstatus = 1 AND ts.name != %(name)s
		  AND tl.task IN %(tasks)s AND tl.from_time >= %(start)s AND tl.from_time < %(end)s
		GROUP BY tl.task, DATE_FORMAT(tl.from_time, '%%b %%Y')
		"""
		+ (" FOR UPDATE" if lock else ""),
		{"employee": employee, "name": name or "", "tasks": tasks, "start": start, "end": end},
		as_dict=True,
	)
	usage = {(r.task, r.month): float(r.hours or 0) for r in used}
	return allocation, usage
