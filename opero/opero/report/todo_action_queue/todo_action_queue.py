from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import date_diff
from frappe.utils import getdate
from frappe.utils import nowdate

from opero import todo_dashboard


def execute(filters=None):
	filters = todo_dashboard.parse_filters(filters)
	columns = get_columns()
	data = get_data(filters)
	return columns, data


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
		{"fieldname": "assignees", "label": _("Assignees"), "fieldtype": "Data", "width": 220},
		{
			"fieldname": "created_by",
			"label": _("Created By"),
			"fieldtype": "Link",
			"options": "User",
			"width": 170,
		},
		{"fieldname": "age_days", "label": _("Age (days)"), "fieldtype": "Int", "width": 100},
	]


def get_data(filters):
	statuses = todo_dashboard.get_default_action_queue_statuses(filters)
	today = getdate(nowdate())
	current_user = frappe.session.user
	assignee_filter = (filters.get("assignee") or "").strip()

	conditions = []
	params = []

	if statuses:
		placeholders = ", ".join(["%s"] * len(statuses))
		conditions.append(f"todo.status IN ({placeholders})")
		params.extend(statuses)

	priority = (filters.get("priority") or "").strip()
	if priority:
		conditions.append("todo.priority = %s")
		params.append(priority)

	if filters.get("from_date"):
		conditions.append("todo.date >= %s")
		params.append(filters.get("from_date"))

	if filters.get("to_date"):
		conditions.append("todo.date <= %s")
		params.append(filters.get("to_date"))

	if filters.get("show_only_overdue"):
		conditions.append("todo.status IN ('Open', 'In Progress')")
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
	else:
		conditions.append(
			"""(
				todo.owner = %s
				OR todo.allocated_to = %s
				OR EXISTS (
					SELECT 1
					FROM `tabToDo Assignee` assignee_row
					WHERE assignee_row.parent = todo.name
						AND assignee_row.parenttype = 'ToDo'
						AND assignee_row.user = %s
				)
			)"""
		)
		params.extend([current_user, current_user, current_user])

	if not conditions:
		conditions.append("1 = 1")

	query = f"""
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
			todo.creation,
			todo.custom_closed_on,
			todo.custom_cancelled_on
		FROM `tabToDo` todo
		WHERE {' AND '.join(conditions)}
		ORDER BY
			CASE
				WHEN todo.status IN ('Open', 'In Progress') AND todo.date IS NOT NULL AND todo.date < %s THEN 0
				WHEN todo.status IN ('Open', 'In Progress') AND todo.date = %s THEN 1
				ELSE 2
			END,
			CASE todo.priority
				WHEN 'High' THEN 0
				WHEN 'Medium' THEN 1
				WHEN 'Low' THEN 2
				ELSE 3
			END,
			todo.date ASC,
			todo.modified DESC
	"""

	params.extend([today, today])
	rows = frappe.db.sql(query, params, as_dict=True)
	if not rows:
		return []

	names = [row.name for row in rows]
	assignee_map = todo_dashboard.get_todo_assignees(names)

	data = []
	for row in rows:
		created_on = getdate(row.creation) if row.creation else today
		assignees = assignee_map.get(row.name) or ([row.allocated_to] if row.allocated_to else [])

		data.append(
			{
				"todo": row.name,
				"title": todo_dashboard.get_todo_title(row),
				"status": row.status,
				"priority": row.priority,
				"due_date": row.date,
				"due_context": todo_dashboard.get_due_date_context(row),
				"assignees": ", ".join(assignees),
				"created_by": row.custom_created_by or row.owner,
				"age_days": max(0, date_diff(today, created_on)),
			}
		)

	return data
