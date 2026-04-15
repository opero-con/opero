from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime

import frappe
from frappe import _
from frappe.utils import add_days
from frappe.utils import cint
from frappe.utils import date_diff
from frappe.utils import flt
from frappe.utils import get_datetime
from frappe.utils import getdate
from frappe.utils import nowdate
from frappe.utils.data import strip_html
from frappe.utils.html_utils import unescape_html

ACTIVE_STATUSES = ("Open", "In Progress")
COMPLETED_STATUSES = ("Closed", "Cancelled")
HIGH_PRIORITY_VALUES = {"High", "Urgent"}


def parse_multi_select(value) -> list[str]:
	if not value:
		return []

	if isinstance(value, str):
		items = [token.strip() for token in value.replace("\n", ",").split(",")]
		return [item for item in items if item]

	if isinstance(value, Iterable):
		items = []
		for token in value:
			text = str(token).strip()
			if text:
				items.append(text)
		return items

	return []


def parse_filters(filters) -> frappe._dict:
	if not filters:
		return frappe._dict()

	if isinstance(filters, str):
		filters = frappe.parse_json(filters) or {}

	return frappe._dict(filters)


def get_reporting_window(filters=None, default_days: int = 30) -> tuple[date, date]:
	parsed = parse_filters(filters)
	to_date = _to_date(parsed.get("to_date")) or getdate(nowdate())
	from_date = _to_date(parsed.get("from_date")) or getdate(add_days(to_date, -(default_days - 1)))

	if from_date > to_date:
		from_date, to_date = to_date, from_date

	return from_date, to_date


def get_todo_title(row) -> str:
	title = extract_plain_text(getattr(row, "custom_title", None) if hasattr(row, "custom_title") else row.get("custom_title"))
	if title:
		return title

	description = extract_plain_text(
		getattr(row, "description", None) if hasattr(row, "description") else row.get("description")
	)
	if description:
		return description

	name = getattr(row, "name", None) if hasattr(row, "name") else row.get("name")
	return name or ""


def extract_plain_text(value: str | None) -> str:
	if not value:
		return ""

	text = unescape_html(strip_html(value))
	return " ".join(text.split()).strip()


def get_due_date_context(row) -> str:
	status = _to_text(_get_value(row, "status"))
	due_date = _to_date(_get_value(row, "date"))

	if status in COMPLETED_STATUSES:
		return get_completion_vs_due_label(status, _get_completion_date(row), due_date)

	if not due_date:
		return ""

	today = getdate(nowdate())
	day_diff = date_diff(due_date, today)

	if day_diff == 0:
		return _("Due today")
	if day_diff == 1:
		return _("Due tomorrow")
	if day_diff > 1:
		return _("Due in {0} days").format(day_diff)
	if day_diff == -1:
		return _("Overdue by 1 day")
	return _("Overdue by {0} days").format(abs(day_diff))


def get_completion_vs_due_label(status: str, completion_date: date | None, due_date: date | None) -> str:
	status_label = _("Closed") if status == "Closed" else _("Cancelled")

	if not completion_date or not due_date:
		return status_label

	day_diff = date_diff(completion_date, due_date)
	if day_diff == 0:
		return _("{0} on due date").format(status_label)
	if day_diff < 0:
		return _("{0} {1}d before due date").format(status_label, abs(day_diff))
	return _("{0} {1}d after due date").format(status_label, day_diff)


def get_todo_assignees(todo_names: list[str]) -> dict[str, list[str]]:
	if not todo_names:
		return {}

	placeholders = ", ".join(["%s"] * len(todo_names))
	rows = frappe.db.sql(
		f"""
			SELECT parent, user
			FROM `tabToDo Assignee`
			WHERE parenttype = 'ToDo'
				AND parent IN ({placeholders})
			ORDER BY idx ASC
		""",
		todo_names,
		as_dict=True,
	)

	assignee_map: dict[str, list[str]] = defaultdict(list)
	for row in rows:
		assignee = _to_text(row.user)
		if assignee and assignee not in assignee_map[row.parent]:
			assignee_map[row.parent].append(assignee)

	return assignee_map


def get_completion_metrics(filters=None, default_days: int = 30) -> dict[str, float]:
	from_date, to_date = get_reporting_window(filters, default_days=default_days)
	closed_on_expr = _date_expr("custom_closed_on")
	cancelled_on_expr = _date_expr("custom_cancelled_on")

	rows = frappe.db.sql(
		f"""
			SELECT status, date, custom_closed_on, custom_cancelled_on
			FROM `tabToDo`
			WHERE date IS NOT NULL
				AND (
					(status = 'Closed' AND custom_closed_on IS NOT NULL
						AND {closed_on_expr} BETWEEN %s AND %s)
					OR
					(status = 'Cancelled' AND custom_cancelled_on IS NOT NULL
						AND {cancelled_on_expr} BETWEEN %s AND %s)
				)
		""",
		[from_date, to_date, from_date, to_date],
		as_dict=True,
	)

	total = 0
	on_time = 0
	delay_sum = 0.0

	for row in rows:
		due_date = _to_date(row.date)
		completion_date = _get_completion_date(row)
		if not due_date or not completion_date:
			continue

		total += 1
		delay_days = date_diff(completion_date, due_date)
		delay_sum += delay_days
		if delay_days <= 0:
			on_time += 1

	return {
		"from_date": from_date,
		"to_date": to_date,
		"total": total,
		"on_time": on_time,
		"on_time_rate": flt((on_time / total) * 100 if total else 0, 2),
		"avg_delay": flt((delay_sum / total) if total else 0, 2),
	}


@frappe.whitelist()
def get_todo_on_time_close_rate(filters=None):
	metrics = get_completion_metrics(filters=filters, default_days=30)
	return {
		"value": metrics["on_time_rate"],
		"fieldtype": "Percent",
		"route": ["query-report", "ToDo Action Queue"],
		"route_options": {
			"status": ["Closed", "Cancelled"],
			"from_date": str(metrics["from_date"]),
			"to_date": str(metrics["to_date"]),
		},
	}


@frappe.whitelist()
def get_todo_avg_closure_delay(filters=None):
	metrics = get_completion_metrics(filters=filters, default_days=30)
	return {
		"value": metrics["avg_delay"],
		"fieldtype": "Float",
		"route": ["query-report", "ToDo Action Queue"],
		"route_options": {
			"status": ["Closed", "Cancelled"],
			"from_date": str(metrics["from_date"]),
			"to_date": str(metrics["to_date"]),
		},
	}


@frappe.whitelist()
def get_my_overdue_todos_count(filters=None):
	today = getdate(nowdate())
	value = _count_todos_for_user(
		statuses=ACTIVE_STATUSES,
		extra_conditions=["todo.date IS NOT NULL", "todo.date < %s"],
		extra_params=[today],
	)
	return {
		"value": value,
		"fieldtype": "Int",
		"route": ["query-report", "ToDo Action Queue"],
		"route_options": {"status": list(ACTIVE_STATUSES), "show_only_overdue": 1},
	}


@frappe.whitelist()
def get_my_todos_due_today_count(filters=None):
	today = getdate(nowdate())
	value = _count_todos_for_user(
		statuses=ACTIVE_STATUSES,
		extra_conditions=["todo.date = %s"],
		extra_params=[today],
	)
	return {
		"value": value,
		"fieldtype": "Int",
		"route": ["query-report", "ToDo Action Queue"],
		"route_options": {
			"status": list(ACTIVE_STATUSES),
			"from_date": str(today),
			"to_date": str(today),
		},
	}


@frappe.whitelist()
def get_my_in_progress_todos_count(filters=None):
	value = _count_todos_for_user(statuses=["In Progress"])
	return {
		"value": value,
		"fieldtype": "Int",
		"route": ["query-report", "ToDo Action Queue"],
		"route_options": {"status": ["In Progress"]},
	}


@frappe.whitelist()
def get_todo_due_next_days_count(filters=None):
	parsed = parse_filters(filters)
	window_days = max(1, cint(parsed.get("window_days") or 3))
	today = getdate(nowdate())
	from_date = getdate(add_days(today, 1))
	to_date = getdate(add_days(today, window_days))
	user_scope_sql, user_scope_params = _get_user_scope_condition("todo")

	count = frappe.db.sql(
		f"""
			SELECT COUNT(DISTINCT todo.name)
				FROM `tabToDo` todo
				WHERE todo.status IN ('Open', 'In Progress')
					AND todo.date IS NOT NULL
					AND todo.date BETWEEN %s AND %s
					AND {user_scope_sql}
			""",
		[from_date, to_date, *user_scope_params],
	)[0][0]

	return {
		"value": cint(count or 0),
		"fieldtype": "Int",
		"route": ["query-report", "ToDo Action Queue"],
		"route_options": {
			"status": ["Open", "In Progress"],
			"from_date": str(from_date),
			"to_date": str(to_date),
		},
	}


@frappe.whitelist()
def get_todo_stale_in_progress_count(filters=None):
	parsed = parse_filters(filters)
	stale_days = max(1, cint(parsed.get("stale_days") or 7))
	cutoff_date = getdate(add_days(nowdate(), -stale_days))
	user_scope_sql, user_scope_params = _get_user_scope_condition("todo")
	modified_expr = _date_expr("todo.modified")

	count = frappe.db.sql(
		f"""
			SELECT COUNT(DISTINCT todo.name)
			FROM `tabToDo` todo
			WHERE todo.status = 'In Progress'
				AND {modified_expr} <= %s
				AND {user_scope_sql}
		""",
		[cutoff_date, *user_scope_params],
	)[0][0]

	return {
		"value": cint(count or 0),
		"fieldtype": "Int",
		"route": ["query-report", "ToDo In Progress Aging"],
		"route_options": {
			"status": ["In Progress"],
			"min_days": stale_days,
		},
	}


@frappe.whitelist()
def get_flow_hub_snapshot(filters=None):
	parsed = parse_filters(filters)
	window_days = max(1, cint(parsed.get("window_days") or 3))
	stale_days = max(1, cint(parsed.get("stale_days") or 7))
	list_limit = max(3, min(20, cint(parsed.get("list_limit") or 8)))

	cards = [
		_build_flow_hub_card("overdue", _("Overdue"), get_my_overdue_todos_count(filters), "#ef4444"),
		_build_flow_hub_card("due_today", _("Due Today"), get_my_todos_due_today_count(filters), "#f97316"),
		_build_flow_hub_card(
			"due_soon",
			_("Due Next {0}d").format(window_days),
			get_todo_due_next_days_count({"window_days": window_days}),
			"#2563eb",
		),
		_build_flow_hub_card(
			"in_progress",
			_("In Progress"),
			get_my_in_progress_todos_count(filters),
			"#1d4ed8",
		),
		_build_flow_hub_card(
			"stale_progress",
			_("Stale {0}d+").format(stale_days),
			get_todo_stale_in_progress_count({"stale_days": stale_days}),
			"#7c3aed",
		),
		_build_flow_hub_card(
			"on_time_rate",
			_("On-time Rate (30d)"),
			get_todo_on_time_close_rate(filters),
			"#059669",
		),
		_build_flow_hub_card(
			"avg_delay",
			_("Avg Delay (30d)"),
			get_todo_avg_closure_delay(filters),
			"#0f766e",
		),
	]

	return {
		"active_total": _count_todos_for_user(statuses=ACTIVE_STATUSES),
		"window_days": window_days,
		"stale_days": stale_days,
		"cards": cards,
		"upcoming": _get_flow_hub_rows(list(ACTIVE_STATUSES), list_limit, completed_first=False),
		"recently_finished": _get_flow_hub_rows(list(COMPLETED_STATUSES), list_limit, completed_first=True),
		"updated_at": str(get_datetime()),
	}


def get_default_action_queue_statuses(filters=None) -> list[str]:
	parsed = parse_filters(filters)
	statuses = parse_multi_select(parsed.get("status"))
	if statuses:
		return statuses
	return list(ACTIVE_STATUSES)


def _build_flow_hub_card(key: str, label: str, metric: dict, accent: str) -> dict:
	fieldtype = _to_text(metric.get("fieldtype")) or "Int"
	if fieldtype in ("Float", "Percent", "Currency"):
		value = flt(metric.get("value") or 0, 2)
	else:
		value = cint(metric.get("value") or 0)

	return {
		"key": key,
		"label": label,
		"value": value,
		"fieldtype": fieldtype,
		"route": metric.get("route") or [],
		"route_options": metric.get("route_options") or {},
		"accent": accent,
	}


def _get_flow_hub_rows(statuses: list[str], limit: int, completed_first: bool = False) -> list[dict]:
	if not statuses:
		return []

	status_placeholders = ", ".join(["%s"] * len(statuses))
	user_scope_sql, user_scope_params = _get_user_scope_condition("todo")
	order_by = (
		"COALESCE(todo.custom_closed_on, todo.custom_cancelled_on, todo.modified) DESC"
		if completed_first
		else "CASE WHEN todo.date IS NULL THEN 1 ELSE 0 END, todo.date ASC, todo.modified DESC"
	)

	rows = frappe.db.sql(
		f"""
			SELECT
				todo.name,
				todo.custom_title,
				todo.description,
				todo.status,
				todo.priority,
				todo.date,
				todo.custom_closed_on,
				todo.custom_cancelled_on,
				todo.modified
			FROM `tabToDo` todo
			WHERE todo.status IN ({status_placeholders})
				AND {user_scope_sql}
			ORDER BY {order_by}
			LIMIT %s
		""",
		[*statuses, *user_scope_params, limit],
		as_dict=True,
	)

	return [_serialize_flow_hub_row(row) for row in rows]


def _serialize_flow_hub_row(row) -> dict:
	name = _to_text(_get_value(row, "name"))
	title = get_todo_title(row) or name
	priority = _to_text(_get_value(row, "priority"))
	due_date = _to_date(_get_value(row, "date"))
	completion_date = _get_completion_date(row)

	return {
		"name": name,
		"title": title,
		"status": _to_text(_get_value(row, "status")),
		"priority": priority,
		"is_high_priority": priority in HIGH_PRIORITY_VALUES,
		"due_date": str(due_date) if due_date else "",
		"due_label": get_due_date_context(row),
		"completion_date": str(completion_date) if completion_date else "",
	}


def serialize_json(value) -> str:
	return json.dumps(value, separators=(",", ":"))


def _to_text(value) -> str:
	return cstr(value).strip()


def _to_date(value) -> date | None:
	if not value:
		return None

	if isinstance(value, date) and not isinstance(value, datetime):
		return value

	try:
		return getdate(value)
	except Exception:
		return None


def _get_completion_date(row) -> date | None:
	status = _to_text(_get_value(row, "status"))
	if status == "Closed":
		return _to_date(_get_value(row, "custom_closed_on"))
	if status == "Cancelled":
		return _to_date(_get_value(row, "custom_cancelled_on"))
	return None


def _get_value(row, fieldname: str):
	if hasattr(row, fieldname):
		return getattr(row, fieldname)
	return row.get(fieldname)


def _date_expr(fieldname: str) -> str:
	if frappe.db.db_type == "postgres":
		return f"CAST({fieldname} AS DATE)"
	return f"DATE({fieldname})"


def _count_todos_for_user(
	statuses: list[str] | tuple[str, ...] | None = None,
	extra_conditions: list[str] | None = None,
	extra_params: list | None = None,
) -> int:
	conditions = []
	params = []

	if statuses:
		placeholders = ", ".join(["%s"] * len(statuses))
		conditions.append(f"todo.status IN ({placeholders})")
		params.extend(statuses)

	if extra_conditions:
		conditions.extend(extra_conditions)
		params.extend(extra_params or [])

	user_scope_sql, user_scope_params = _get_user_scope_condition("todo")
	conditions.append(user_scope_sql)
	params.extend(user_scope_params)

	if not conditions:
		conditions.append("1 = 1")

	count = frappe.db.sql(
		f"""
			SELECT COUNT(DISTINCT todo.name)
			FROM `tabToDo` todo
			WHERE {' AND '.join(conditions)}
		""",
		params,
	)[0][0]
	return cint(count or 0)


def _get_user_scope_condition(alias: str = "todo") -> tuple[str, list[str]]:
	current_user = frappe.session.user
	return (
		f"""(
			{alias}.owner = %s
			OR {alias}.allocated_to = %s
			OR EXISTS (
				SELECT 1
				FROM `tabToDo Assignee` assignee_row
				WHERE assignee_row.parent = {alias}.name
					AND assignee_row.parenttype = 'ToDo'
					AND assignee_row.user = %s
			)
		)""",
		[current_user, current_user, current_user],
	)


def cstr(value) -> str:
	if value is None:
		return ""
	return str(value)
