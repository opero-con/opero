from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days
from frappe.utils import cint
from frappe.utils import date_diff
from frappe.utils import flt
from frappe.utils import getdate
from frappe.utils import nowdate

from opero import todo_dashboard


def execute(filters=None):
	filters = todo_dashboard.parse_filters(filters)
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data, filters)
	report_summary = get_summary(data)
	return columns, data, None, chart, report_summary


def get_columns():
	return [
		{
			"fieldname": "assignee",
			"label": _("Assignee"),
			"fieldtype": "Link",
			"options": "User",
			"width": 200,
		},
		{
			"fieldname": "active_count",
			"label": _("Active"),
			"fieldtype": "Int",
			"width": 90,
		},
		{
			"fieldname": "overdue_count",
			"label": _("Overdue"),
			"fieldtype": "Int",
			"width": 90,
		},
		{
			"fieldname": "due_today_count",
			"label": _("Due Today"),
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"fieldname": "high_priority_active_count",
			"label": _("High Priority Active"),
			"fieldtype": "Int",
			"width": 160,
		},
		{
			"fieldname": "closed_7d",
			"label": _("Closed/Cancelled (7d)"),
			"fieldtype": "Int",
			"width": 160,
		},
		{
			"fieldname": "on_time_rate_30d",
			"label": _("On-time %"),
			"fieldtype": "Int",
			"width": 110,
		},
		{
			"fieldname": "avg_delay_30d",
			"label": _("Avg Delay (days)"),
			"fieldtype": "Float",
			"precision": 1,
			"width": 140,
		},
		{
			"fieldname": "risk_score",
			"label": _("Risk Score"),
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"fieldname": "risk_band",
			"label": _("Risk Band"),
			"fieldtype": "Data",
			"width": 100,
		},
	]


def get_data(filters):
	today = getdate(nowdate())
	seven_days_ago = getdate(add_days(today, -6))
	thirty_days_ago = getdate(add_days(today, -29))
	# Default window for completed todos: 90 days. Bypass with include_historical=1.
	history_cutoff = getdate(add_days(today, -89))

	conditions = []
	params = []

	entity_sql, entity_params = todo_dashboard.get_entity_condition(filters)
	if entity_sql:
		conditions.append(entity_sql)
		params.extend(entity_params)

	assignee = (filters.get("assignee") or "").strip()
	if assignee:
		conditions.append(
			"""(
				todo.allocated_to = %s
				OR EXISTS (
					SELECT 1
					FROM `tabToDo Assignee` assignee_row
					WHERE assignee_row.parent = todo.name
						AND assignee_row.parenttype = 'ToDo'
						AND assignee_row.user = %s
				)
			)"""
		)
		params.extend([assignee, assignee])

	if not cint(filters.get("include_historical")):
		closed_on_expr = _date_expr("todo.custom_closed_on")
		cancelled_on_expr = _date_expr("todo.custom_cancelled_on")
		conditions.append(
			f"""(
				todo.status IN ('Open', 'In Progress')
				OR (
					todo.status IN ('Closed', 'Cancelled')
					AND COALESCE({closed_on_expr}, {cancelled_on_expr}) >= %s
				)
			)"""
		)
		params.append(history_cutoff)

	if not conditions:
		conditions.append("1 = 1")

	todo_rows = frappe.db.sql(
		f"""
			SELECT
				todo.name,
				todo.allocated_to,
				todo.status,
				todo.priority,
				todo.date,
				todo.custom_closed_on,
				todo.custom_cancelled_on
			FROM `tabToDo` todo
			WHERE {' AND '.join(conditions)}
		""",
		params,
		as_dict=True,
	)

	if not todo_rows:
		return []

	assignee_map = todo_dashboard.get_todo_assignees([row.name for row in todo_rows])
	metrics = defaultdict(
		lambda: {
			"active_count": 0,
			"overdue_count": 0,
			"due_today_count": 0,
			"high_priority_active_count": 0,
			"closed_7d": 0,
			"completed_30d": 0,
			"on_time_30d": 0,
			"delay_sum_30d": 0.0,
		}
	)

	for row in todo_rows:
		todo_assignees = assignee_map.get(row.name, [])
		if row.allocated_to and row.allocated_to not in todo_assignees:
			todo_assignees.append(row.allocated_to)
		if not todo_assignees:
			continue

		status = row.status
		due_date = getdate(row.date) if row.date else None
		completion_date = _get_completion_date(status, row.custom_closed_on, row.custom_cancelled_on)

		for assignee_id in todo_assignees:
			user_metrics = metrics[assignee_id]

			if status in todo_dashboard.ACTIVE_STATUSES:
				user_metrics["active_count"] += 1

				if due_date:
					if due_date < today:
						user_metrics["overdue_count"] += 1
					elif due_date == today:
						user_metrics["due_today_count"] += 1

				if row.priority in todo_dashboard.HIGH_PRIORITY_VALUES:
					user_metrics["high_priority_active_count"] += 1

			if not completion_date:
				continue

			if completion_date >= seven_days_ago:
				user_metrics["closed_7d"] += 1

			if completion_date < thirty_days_ago or not due_date:
				continue

			delay_days = date_diff(completion_date, due_date)
			user_metrics["completed_30d"] += 1
			user_metrics["delay_sum_30d"] += delay_days
			if delay_days <= 0:
				user_metrics["on_time_30d"] += 1

	if not metrics:
		return []

	user_ids = list(metrics)
	users = frappe.get_all(
		"User",
		filters={"name": ("in", user_ids)},
		fields=["name", "full_name", "enabled"],
		limit_page_length=0,
	)
	user_map = {user.name: user for user in users}
	include_disabled = cint(filters.get("include_disabled_users"))

	data = []
	for assignee_id, user_metrics in metrics.items():
		user = user_map.get(assignee_id)
		if user and not include_disabled and not cint(user.enabled):
			continue

		completed_30d = user_metrics["completed_30d"]
		on_time_rate = round((user_metrics["on_time_30d"] / completed_30d) * 100 if completed_30d else 0)
		avg_delay = flt((user_metrics["delay_sum_30d"] / completed_30d) if completed_30d else 0, 2)
		risk_score = _get_risk_score(user_metrics)

		data.append(
			{
				"assignee": assignee_id,
				"assignee_name": (user.full_name if user else assignee_id),
				"active_count": user_metrics["active_count"],
				"overdue_count": user_metrics["overdue_count"],
				"due_today_count": user_metrics["due_today_count"],
				"high_priority_active_count": user_metrics["high_priority_active_count"],
				"closed_7d": user_metrics["closed_7d"],
				"on_time_rate_30d": on_time_rate,
				"avg_delay_30d": avg_delay,
				"risk_score": risk_score,
				"risk_band": _get_risk_band(risk_score),
			}
		)

	data.sort(
		key=lambda row: (
			-row["risk_score"],
			-row["overdue_count"],
			-row["active_count"],
			row["assignee_name"],
		)
	)
	return data


def get_chart(data, filters):
	top_n = max(1, cint(filters.get("top_n") or 10))
	top_rows = data[:top_n]
	if not top_rows:
		return None

	return {
		"data": {
			"labels": [row.get("assignee_name") or row.get("assignee") for row in top_rows],
			"datasets": [
				{"name": _("Active"), "values": [row.get("active_count") for row in top_rows]},
				{"name": _("Overdue"), "values": [row.get("overdue_count") for row in top_rows]},
				{
					"name": _("High Priority Active"),
					"values": [row.get("high_priority_active_count") for row in top_rows],
				},
			],
		},
		"type": "bar",
		"colors": ["#2563EB", "#DC2626", "#D97706"],
	}


def get_summary(data):
	if not data:
		return []

	total_active = sum(cint(row.get("active_count")) for row in data)
	total_overdue = sum(cint(row.get("overdue_count")) for row in data)
	total_due_today = sum(cint(row.get("due_today_count")) for row in data)
	total_high_priority = sum(cint(row.get("high_priority_active_count")) for row in data)
	critical_assignees = sum(1 for row in data if row.get("risk_band") == "Critical")

	return [
		{"label": _("Total Active"), "value": total_active, "datatype": "Int"},
		{"label": _("Total Overdue"), "value": total_overdue, "datatype": "Int"},
		{"label": _("Due Today"), "value": total_due_today, "datatype": "Int"},
		{"label": _("High Priority Active"), "value": total_high_priority, "datatype": "Int"},
		{"label": _("Critical Assignees"), "value": critical_assignees, "datatype": "Int"},
	]


def _date_expr(fieldname: str) -> str:
	if frappe.db.db_type == "postgres":
		return f"CAST({fieldname} AS DATE)"
	return f"DATE({fieldname})"


def _get_completion_date(status, closed_on, cancelled_on):
	if status == "Closed" and closed_on:
		return getdate(closed_on)
	if status == "Cancelled" and cancelled_on:
		return getdate(cancelled_on)
	return None


def _get_risk_score(metrics) -> int:
	active_count = cint(metrics.get("active_count"))
	overdue_count = cint(metrics.get("overdue_count"))
	due_today_count = cint(metrics.get("due_today_count"))
	high_priority_count = cint(metrics.get("high_priority_active_count"))
	capacity_overflow = max(active_count - 8, 0)
	return (overdue_count * 4) + (high_priority_count * 3) + (due_today_count * 2) + capacity_overflow


def _get_risk_band(score: int) -> str:
	if score >= 20:
		return "Critical"
	if score >= 12:
		return "High"
	if score >= 6:
		return "Medium"
	return "Low"
