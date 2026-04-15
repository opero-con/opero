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
	summary = get_summary(data)
	return columns, data, None, None, summary


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
		{"fieldname": "reference_type", "label": _("Ref Type"), "fieldtype": "Data", "width": 120},
		{
			"fieldname": "reference_name",
			"label": _("Ref Name"),
			"fieldtype": "Dynamic Link",
			"options": "reference_type",
			"width": 160,
		},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "priority", "label": _("Priority"), "fieldtype": "Data", "width": 110},
		{"fieldname": "due_date", "label": _("Due Date"), "fieldtype": "Date", "width": 120},
		{"fieldname": "due_context", "label": _("Due Context"), "fieldtype": "Data", "width": 200},
		{"fieldname": "assignees", "label": _("Assignees"), "fieldtype": "Data", "width": 220},
		{
			"fieldname": "created_by",
			"label": _("Created By"),
			"fieldtype": "Link",
			"options": "User",
			"width": 160,
		},
		{"fieldname": "age_days", "label": _("Age (days)"), "fieldtype": "Int", "width": 90},
	]


def get_data(filters):
	statuses = todo_dashboard.get_default_action_queue_statuses(filters)
	today = getdate(nowdate())
	current_user = frappe.session.user
	assignee_filter = (filters.get("assignee") or "").strip()

	# show_only_overdue requires active statuses - override whatever the status filter says
	if filters.get("show_only_overdue"):
		statuses = [s for s in statuses if s in todo_dashboard.ACTIVE_STATUSES] or list(
			todo_dashboard.ACTIVE_STATUSES
		)

	conditions = []
	params = []

	if statuses:
		placeholders = ", ".join(["%s"] * len(statuses))
		conditions.append(f"todo.status IN ({placeholders})")
		params.extend(statuses)

	priority_values = todo_dashboard.parse_multi_select(filters.get("priority"))
	if priority_values:
		placeholders = ", ".join(["%s"] * len(priority_values))
		conditions.append(f"todo.priority IN ({placeholders})")
		params.extend(priority_values)

	if filters.get("from_date"):
		conditions.append("todo.date >= %s")
		params.append(filters.get("from_date"))

	if filters.get("to_date"):
		conditions.append("todo.date <= %s")
		params.append(filters.get("to_date"))

	if filters.get("show_only_overdue"):
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
			todo.reference_type,
			todo.reference_name,
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
				WHEN 'Urgent' THEN 0
				WHEN 'High' THEN 1
				WHEN 'Medium' THEN 2
				WHEN 'Low' THEN 3
				ELSE 4
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
		due_date = row.date

		data.append(
			{
				"todo": row.name,
				"title": todo_dashboard.get_todo_title(row),
				"reference_type": row.reference_type or "",
				"reference_name": row.reference_name or "",
				"status": row.status,
				"priority": row.priority,
				"due_date": due_date,
				"due_context": todo_dashboard.get_due_date_context(row),
				"assignees": ", ".join(assignees),
				"created_by": row.custom_created_by or row.owner,
				"age_days": max(0, date_diff(today, created_on)),
				"indicator": _get_indicator(row.status, due_date, today),
			}
		)

	return data


def get_summary(data):
	total = len(data)
	overdue = sum(1 for row in data if row.get("indicator") == "red")
	due_today = sum(1 for row in data if row.get("indicator") == "orange")
	in_progress = sum(1 for row in data if row.get("status") == "In Progress")

	return [
		{"label": _("Showing"), "value": total, "datatype": "Int"},
		{"label": _("Overdue"), "value": overdue, "datatype": "Int"},
		{"label": _("Due Today"), "value": due_today, "datatype": "Int"},
		{"label": _("In Progress"), "value": in_progress, "datatype": "Int"},
	]


def _get_indicator(status, due_date, today) -> str:
	if status == "Closed":
		return "green"
	if status == "Cancelled":
		return "grey"
	if due_date:
		due = getdate(due_date) if not isinstance(due_date, type(today)) else due_date
		if due < today:
			return "red"
		if due == today:
			return "orange"
	if status == "In Progress":
		return "blue"
	return ""
