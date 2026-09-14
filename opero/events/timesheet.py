"""Timesheet validators ported from FC Server Scripts."""

from __future__ import annotations

import frappe
from frappe.utils import add_to_date, escape_html, get_datetime


def validate_timesheet(doc, _method=None):
	_set_week_of_month(doc)
	_anti_spill(doc)
	_fetch_pm_email(doc)
	_validate_allocated_hours(doc)


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
			f"Row {row.idx}: this entry crosses midnight. Use Split at midnight to preserve its times.",
			title="Split time entry",
		)


def _fetch_pm_email(doc):
	doc.custom_pm_email = (
		frappe.db.get_value("Project", doc.parent_project, "custom_pm_email") if doc.parent_project else None
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
			frappe.throw(
				f"Task <b>{_safe_html(task)}</b>, {_safe_html(month)}: allocated {budget:g}h, "
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


def get_monthly_balances(employee, rows, name=None, lock=False):
	tasks = sorted({row.task for row in rows})
	allocated = frappe.db.sql(
		"""
		SELECT t.project_task AS task, s.month, SUM(s.time_spread) AS hours
		FROM `tabTask Time Distribution` t
		JOIN `tabTask Time Distribution Spread` s ON s.parent = t.name
		WHERE t.personnel = %(employee)s AND t.project_task IN %(tasks)s
		GROUP BY t.project_task, s.month
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
