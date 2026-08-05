"""Timesheet validators ported from FC Server Scripts."""

from __future__ import annotations

import frappe
from frappe.utils import add_to_date, escape_html, format_datetime, get_datetime


MONTH_MAP = {
	"01": "Jan",
	"02": "Feb",
	"03": "Mar",
	"04": "Apr",
	"05": "May",
	"06": "Jun",
	"07": "Jul",
	"08": "Aug",
	"09": "Sep",
	"10": "Oct",
	"11": "Nov",
	"12": "Dec",
}


def validate_timesheet(doc, _method=None):
	_anti_spill(doc)
	_fetch_pm_email(doc)
	_validate_allocated_hours(doc)


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

		day_end = get_datetime(f"{ft.date()} 23:59:59")
		new_from = add_to_date(day_end, seconds=-intended_seconds)
		if new_from.date() != ft.date():
			frappe.throw(
				f"Row {row.idx}: {hrs}h cannot fit on {ft.date()} without crossing midnight. "
				"Please split this entry at midnight."
			)

		row.from_time = new_from
		row.to_time = add_to_date(new_from, seconds=intended_seconds)
		frappe.msgprint(
			f"Row {row.idx}: Start shifted to {format_datetime(new_from)} "
			f"so that {hrs}h ends within {ft.date()}."
		)


def _fetch_pm_email(doc):
	if doc.parent_project:
		doc.custom_pm_email = frappe.db.get_value("Project", doc.parent_project, "custom_pm_email")


def _validate_allocated_hours(doc):
	for row in doc.time_logs or []:
		if not (doc.employee and row.task and row.from_time):
			continue

		task_label = f"<b>{_safe_html(row.custom_project_task or row.task)}</b>"
		pm_display = f"<b>{_safe_html(_pm_name_from_parent_project(doc.parent_project) or 'PM')}</b>"

		try:
			from_str = str(row.from_time)
			year = from_str[:4]
			month_num = from_str[5:7]
			if month_num not in MONTH_MAP:
				frappe.throw(f"Invalid month format: {_safe_html(month_num)}")
			month_str = f"{MONTH_MAP[month_num]} {year}"
		except Exception:
			frappe.throw(
				f"Unable to determine month from From Time: <b>{_safe_html(row.from_time)}</b> "
				f"for task {task_label}. Please ensure it is a valid datetime.",
				title="Invalid From Time",
			)

		month_allocated = frappe.db.sql(
			"""
			SELECT 1
			FROM `tabTask Time Distribution Spread` s
			WHERE s.month = %s AND s.time_spread > 0
			  AND EXISTS (
				SELECT 1 FROM `tabTask Time Distribution` t
				WHERE t.name = s.parent
				  AND t.personnel = %s
				  AND t.project_task = %s
			  )
			LIMIT 1
			""",
			(month_str, doc.employee, row.task),
		)
		if not month_allocated:
			frappe.throw(
				f"No time allocated for <b>{_safe_html(month_str)}</b> in task "
				f"{task_label} under TTD.<br>"
				f"Please contact the PM, {pm_display}, for review.",
				title="No Monthly Allocation",
			)

		task_time_data = frappe.db.sql(
			"""
			SELECT SUM(s.time_spread) AS total
			FROM `tabTask Time Distribution Spread` s
			JOIN `tabTask Time Distribution` t ON t.name = s.parent
			WHERE t.personnel = %s AND t.project_task = %s
			""",
			(doc.employee, row.task),
			as_dict=True,
		)
		task_time = float((task_time_data[0].total if task_time_data else 0) or 0)
		current_hours = float(row.hours or 0)
		if hasattr(row, "custom_a_hrs"):
			row.custom_a_hrs = task_time

		if task_time <= 0:
			frappe.throw(
				f"You have no hours assigned for task {task_label} in TTD for this project.<br>"
				f"Please contact the PM, {pm_display}, for review.",
				title="No Hours Allocated",
			)
		if current_hours > task_time:
			frappe.throw(
				f"Logged hours ({_safe_html(current_hours)}) exceed allocated hours "
				f"({_safe_html(task_time)}) for task {task_label}.<br>"
				f"Please contact the PM, {pm_display}, for review.",
				title="Exceeds Allocated Hours",
			)


def _validate_project_rate_factor(doc):
	project = doc.parent_project or ""
	project_name = project
	if project:
		project_name = frappe.db.get_value("Project", project, "project_name") or project

	missing_rows = [str(row.idx or "") for row in (doc.time_logs or []) if not (row.activity_type or "")]
	if not missing_rows:
		return

	has_any = bool(project and frappe.db.exists("Activity Type", {"custom_project": project}))
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
