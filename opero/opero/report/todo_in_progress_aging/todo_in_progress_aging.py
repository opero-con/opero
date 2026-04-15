from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint
from frappe.utils import date_diff
from frappe.utils import getdate
from frappe.utils import nowdate

from opero import todo_dashboard


DEFAULT_STATUSES = ["In Progress"]


def execute(filters=None):
	filters = todo_dashboard.parse_filters(filters)
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	report_summary = get_summary(data)
	return columns, data, None, chart, report_summary


def get_columns():
	return [
		{
			"fieldname": "todo",
			"label": _("ToDo"),
			"fieldtype": "Link",
			"options": "ToDo",
			"width": 140,
		},
		{"fieldname": "title", "label": _("Title"), "fieldtype": "Data", "width": 260},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "priority", "label": _("Priority"), "fieldtype": "Data", "width": 110},
		{"fieldname": "due_date", "label": _("Due Date"), "fieldtype": "Date", "width": 120},
		{"fieldname": "due_context", "label": _("Due Context"), "fieldtype": "Data", "width": 220},
		{"fieldname": "idle_days", "label": _("Idle (days)"), "fieldtype": "Int", "width": 100},
		{"fieldname": "assignees", "label": _("Assignees"), "fieldtype": "Data", "width": 220},
		{
			"fieldname": "created_by",
			"label": _("Created By"),
			"fieldtype": "Link",
			"options": "User",
			"width": 170,
		},
		{
			"fieldname": "last_modified",
			"label": _("Last Activity"),
			"fieldtype": "Datetime",
			"width": 180,
		},
	]


def get_data(filters):
	today = getdate(nowdate())
	min_days = max(0, cint(filters.get("min_days") or 7))
	assignee_filter = (filters.get("assignee") or "").strip()
	show_all = cint(filters.get("show_all"))
	statuses = todo_dashboard.parse_multi_select(filters.get("status")) or DEFAULT_STATUSES

	conditions = []
	params = []

	if statuses:
		placeholders = ", ".join(["%s"] * len(statuses))
		conditions.append(f"todo.status IN ({placeholders})")
		params.extend(statuses)

	if filters.get("only_overdue"):
		conditions.append("todo.date IS NOT NULL")
		conditions.append("todo.date < %s")
		params.append(today)

	if assignee_filter:
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
		params.extend([assignee_filter, assignee_filter])
	elif not show_all:
		user_scope_sql, user_scope_params = todo_dashboard.get_user_scope_condition("todo")
		conditions.append(user_scope_sql)
		params.extend(user_scope_params)

	if not conditions:
		conditions.append("1 = 1")

	rows = frappe.db.sql(
		f"""
			SELECT
				todo.name,
				todo.custom_title,
				todo.description,
				todo.status,
				todo.priority,
				todo.date,
				todo.allocated_to,
				todo.custom_created_by,
				todo.owner,
				todo.modified
			FROM `tabToDo` todo
			WHERE {' AND '.join(conditions)}
			ORDER BY
				CASE
					WHEN todo.date IS NOT NULL AND todo.date < %s THEN 0
					WHEN todo.date = %s THEN 1
					ELSE 2
				END,
				todo.modified ASC
		""",
		[*params, today, today],
		as_dict=True,
	)

	if not rows:
		return []

	names = [row.name for row in rows]
	assignee_map = todo_dashboard.get_todo_assignees(names)

	data = []
	for row in rows:
		last_activity_date = getdate(row.modified) if row.modified else today
		idle_days = max(0, date_diff(today, last_activity_date))
		if idle_days < min_days:
			continue

		assignees = assignee_map.get(row.name) or ([row.allocated_to] if row.allocated_to else [])
		data.append(
			{
				"todo": row.name,
				"title": todo_dashboard.get_todo_title(row),
				"status": row.status,
				"priority": row.priority,
				"due_date": row.date,
				"due_context": todo_dashboard.get_due_date_context(row),
				"idle_days": idle_days,
				"assignees": ", ".join(assignees),
				"created_by": row.custom_created_by or row.owner,
				"last_modified": row.modified,
			}
		)

	data.sort(key=lambda row: (-row["idle_days"], row.get("due_date") or today, row["title"]))
	return data


def get_chart(data):
	buckets = {
		"0-2d": 0,
		"3-6d": 0,
		"7-13d": 0,
		"14+d": 0,
	}

	for row in data:
		idle_days = cint(row.get("idle_days"))
		if idle_days <= 2:
			buckets["0-2d"] += 1
		elif idle_days <= 6:
			buckets["3-6d"] += 1
		elif idle_days <= 13:
			buckets["7-13d"] += 1
		else:
			buckets["14+d"] += 1

	return {
		"data": {
			"labels": list(buckets),
			"datasets": [
				{
					"name": _("In Progress ToDos"),
					"values": list(buckets.values()),
				}
			],
		},
		"type": "bar",
		"colors": ["#D97706"],
	}


def get_summary(data):
	today = getdate(nowdate())
	total = len(data)
	overdue = sum(1 for row in data if row.get("due_date") and getdate(row.get("due_date")) < today)
	avg_idle_days = 0 if not total else round(sum(cint(row.get("idle_days")) for row in data) / total, 2)

	return [
		{"label": _("In Progress (Filtered)"), "value": total, "datatype": "Int"},
		{"label": _("Overdue"), "value": overdue, "datatype": "Int"},
		{"label": _("Avg Idle Days"), "value": avg_idle_days, "datatype": "Float"},
	]
