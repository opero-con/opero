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
from frappe.utils import cstr
from frappe.utils import get_datetime
from frappe.utils import getdate
from frappe.utils import nowdate
from frappe.utils.data import strip_html
from frappe.utils.html_utils import unescape_html

ACTIVE_STATUSES = ("Open", "In Progress")
COMPLETED_STATUSES = ("Closed", "Cancelled")
HIGH_PRIORITY_VALUES = {"High", "Urgent"}
FLOW_HUB_EDITABLE_FIELDS = {
	"date",
	"priority",
	"status",
	"custom_title",
	"description",
	"reference_type",
	"reference_name",
	"role",
	"color",
	"sender",
	"assignment_rule",
	"assigned_by",
}
FLOW_HUB_DETAIL_FIELDNAMES = (
	"reference_type",
	"reference_name",
	"role",
	"color",
	"sender",
	"assignment_rule",
)


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
		return _("Due in {0}d").format(day_diff)
	if day_diff == -1:
		return _("Overdue by 1d")
	return _("Overdue by {0}d").format(abs(day_diff))


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
def update_todo_from_flow_hub(todo_name: str, values=None, expected_modified: str | None = None):
	"""Update a live ToDo from Flow Hub after checking the row is still current."""
	if isinstance(values, str):
		values = frappe.parse_json(values) or {}

	if not isinstance(values, dict):
		frappe.throw(_("Nothing to update."))

	doc = frappe.get_doc("ToDo", todo_name)
	_assert_flow_hub_todo_is_current(doc, expected_modified)

	unknown_fields = set(values) - FLOW_HUB_EDITABLE_FIELDS
	if unknown_fields:
		frappe.throw(_("Flow Hub cannot update: {0}").format(", ".join(sorted(unknown_fields))))

	if "date" in values:
		doc.date = values.get("date") or None

	if "priority" in values:
		doc.priority = values.get("priority") or None

	if "status" in values:
		status = cstr(values.get("status")).strip()
		if status and status not in (*ACTIVE_STATUSES, *COMPLETED_STATUSES):
			frappe.throw(_("Unsupported ToDo status: {0}").format(status))
		doc.status = status

	if "custom_title" in values:
		doc.custom_title = cstr(values.get("custom_title") or "").strip() or None

	if "description" in values:
		doc.description = cstr(values.get("description") or "").strip() or None

	for fieldname in ("reference_type", "reference_name", "role", "color", "sender", "assignment_rule"):
		if fieldname in values:
			doc.set(fieldname, cstr(values.get(fieldname) or "").strip() or None)

	doc.save(ignore_permissions=True)
	return {"success": True, "modified": cstr(doc.modified), "status": doc.status}


@frappe.whitelist()
def add_todo_assignee(todo_name: str, user: str, as_main_assignee: int = 0, expected_modified: str | None = None):
	"""Add a user to a ToDo's assignees list and save."""
	doc = frappe.get_doc("ToDo", todo_name)
	_assert_flow_hub_todo_is_current(doc, expected_modified)
	existing = [row.user for row in (doc.custom_assignees or []) if row.user]
	is_main = cint(as_main_assignee)

	if user in existing:
		if not is_main:
			return {"success": True}
		existing = [assignee for assignee in existing if assignee != user]

	if is_main:
		updated = [user, *existing]
	else:
		updated = [*existing, user]

	_rebuild_todo_assignees(doc, updated)
	doc.save(ignore_permissions=True)
	return {"success": True}


@frappe.whitelist()
def remove_todo_assignee(todo_name: str, user: str, expected_modified: str | None = None):
	"""Remove a user from a ToDo's assignees list and save."""
	doc = frappe.get_doc("ToDo", todo_name)
	_assert_flow_hub_todo_is_current(doc, expected_modified)
	remaining = [row.user for row in (doc.custom_assignees or []) if row.user and row.user != user]
	_rebuild_todo_assignees(doc, remaining)
	doc.save(ignore_permissions=True)
	return {"success": True}


@frappe.whitelist()
def get_todo_detail_context(todo_name: str):
	"""Return full detail panel payload for a ToDo row."""
	doc = frappe.get_doc("ToDo", todo_name)
	doc.check_permission("read")

	creator_user = cstr(doc.custom_created_by or "")
	beneficiary_user = cstr(doc.assigned_by or "")

	user_names = {}
	users_to_fetch = [u for u in [creator_user, beneficiary_user] if u]
	if users_to_fetch:
		user_names = {
			r.name: _user_display_name(r) or r.name
			for r in frappe.get_all(
				"User",
				filters=[["name", "in", users_to_fetch]],
				fields=_user_fields(include_image=False),
			)
		}

	creator_display = user_names.get(creator_user, creator_user) or cstr(doc.owner)
	created_entry = {
		"name": "created",
		"type": "Created",
		"by": creator_display,
		"content": "",
		"creation": cstr(doc.creation),
	}

	return {
		"description": cstr(doc.description or ""),
		"description_plain": extract_plain_text(doc.description),
		"tags": _get_todo_tags([todo_name]).get(todo_name, []),
		"attachments": _get_todo_attachments(todo_name),
		"activity": _get_todo_activity(todo_name) + [created_entry],
		"field_values": _get_todo_detail_field_values(doc),
		"modified": cstr(doc.modified),
		"creator_user": creator_user,
		"creator_name": user_names.get(creator_user, creator_user),
		"beneficiary_user": beneficiary_user,
		"beneficiary_name": user_names.get(beneficiary_user, beneficiary_user),
	}


def _rebuild_todo_assignees(doc, users: list[str]):
	seen = set()
	ordered_users = []
	for user in users:
		if user and user not in seen:
			seen.add(user)
			ordered_users.append(user)

	doc.set("custom_assignees", [])
	for user in ordered_users:
		doc.append("custom_assignees", {"user": user})

	doc.allocated_to = ordered_users[0] if ordered_users else None


def _assert_flow_hub_todo_is_current(doc, expected_modified: str | None = None):
	if expected_modified and cstr(doc.modified) != cstr(expected_modified):
		frappe.throw(_("This ToDo changed elsewhere. Refresh Flow Hub and try again."))

	if doc.status not in ACTIVE_STATUSES:
		frappe.throw(_("This ToDo is no longer active. Refresh Flow Hub."))


@frappe.whitelist()
def get_todo_on_time_close_rate(filters=None):
	metrics = get_completion_metrics(filters=filters, default_days=30)
	return {
		"value": metrics["on_time_rate"],
		"fieldtype": "Percent",
		"route": ["query-report", "ToDo Explorer"],
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
		"route": ["query-report", "ToDo Explorer"],
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
		"route": ["query-report", "ToDo Explorer"],
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
		"route": ["query-report", "ToDo Explorer"],
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
		"route": ["query-report", "ToDo Explorer"],
		"route_options": {"status": ["In Progress"]},
	}


@frappe.whitelist()
def get_todo_due_next_days_count(filters=None):
	parsed = parse_filters(filters)
	window_days = max(1, cint(parsed.get("window_days") or 3))
	today = getdate(nowdate())
	from_date = getdate(add_days(today, 1))
	to_date = getdate(add_days(today, window_days))
	user_scope_sql, user_scope_params = get_user_scope_condition("todo")

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
		"route": ["query-report", "ToDo Explorer"],
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
	user_scope_sql, user_scope_params = get_user_scope_condition("todo")
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
def get_flow_hub_snapshot(filters=None, force_refresh=0):
	parsed = parse_filters(filters)
	window_days = max(1, cint(parsed.get("window_days") or 3))
	stale_days = max(1, cint(parsed.get("stale_days") or 7))
	list_limit = max(3, min(20, cint(parsed.get("list_limit") or 10)))

	today = getdate(nowdate())
	due_soon_from = getdate(add_days(today, 1))
	due_soon_to = getdate(add_days(today, window_days))
	stale_cutoff = getdate(add_days(today, -stale_days))

	counts = _get_aggregated_user_metrics(today, due_soon_from, due_soon_to, stale_cutoff)
	closed_today = _get_closed_today(today)

	result = {
		"attention": _build_attention_message(closed_today),
		"counts": [
			{
				"key": "overdue",
				"label": _("Overdue"),
				"value": counts["overdue"],
				"accent": "#ef4444",
				"route": ["List", "ToDo", "List"],
				"route_options": {
					"status": ["in", "Open,In Progress"],
					"date": ["<", str(today)],
				},
			},
			{
				"key": "due_today",
				"label": _("Due Today"),
				"value": counts["due_today"],
				"accent": "#f97316",
				"route": ["List", "ToDo", "List"],
				"route_options": {
					"status": ["in", "Open,In Progress"],
					"date": ["=", str(today)],
				},
			},
			{
				"key": "due_soon",
				"label": _("Due Soon"),
				"value": counts["due_soon"],
				"accent": "#2563eb",
				"route": ["List", "ToDo", "List"],
				"route_options": {
					"status": ["in", "Open,In Progress"],
					"date": ["between", [str(due_soon_from), str(due_soon_to)]],
				},
			},
			{
				"key": "in_progress",
				"label": _("In Progress"),
				"value": counts["in_progress"],
				"accent": "#1d4ed8",
				"route": ["List", "ToDo", "List"],
				"route_options": {"status": "In Progress"},
			},
			{
				"key": "stale",
				"label": _("Stale {0}d+").format(stale_days),
				"value": counts["stale"],
				"accent": "#7c3aed",
				"route": ["List", "ToDo", "List"],
				"route_options": {
					"status": "In Progress",
					"modified": ["<=", str(stale_cutoff)],
				},
			},
		],
		"focus_queue": _get_focus_queue(list_limit, stale_cutoff, due_soon_to),
		"risk": [
			{
				"key": "stale",
				"label": _("Stale {0}d+").format(stale_days),
				"value": counts["stale"],
				"route": ["List", "ToDo", "List"],
				"route_options": {
					"status": "In Progress",
					"modified": ["<=", str(stale_cutoff)],
				},
			},
			{
				"key": "no_due_date",
				"label": _("No Due Date"),
				"value": counts["no_due_date"],
				"route": ["List", "ToDo", "List"],
				"route_options": {
					"status": ["in", "Open,In Progress"],
					"date": ["is", "not set"],
				},
			},
			{
				"key": "high_priority",
				"label": _("High Priority Active"),
				"value": counts["high_priority"],
				"route": ["List", "ToDo", "List"],
				"route_options": {
					"status": ["in", "Open,In Progress"],
					"priority": "High",
				},
			},
			{
				"key": "unassigned",
				"label": _("Unallocated"),
				"value": _get_unassigned_active_count(),
				"route": ["List", "ToDo", "List"],
				"route_options": {
					"status": ["in", "Open,In Progress"],
					"allocated_to": ["is", "not set"],
				},
			},
		],
		"throughput_30d": _get_throughput_30d(),
		"active_total": counts["active_total"],
		"stale_days": stale_days,
		"window_days": window_days,
		"updated_at": str(get_datetime()),
	}

	return result


@frappe.whitelist()
def get_closed_todos():
	from datetime import timedelta

	user_scope_sql, user_scope_params = get_user_scope_condition("todo")
	today = getdate(nowdate())
	cutoff = today - timedelta(days=30)
	fetch_limit = 101  # one extra to detect overflow

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
				todo.modified,
				todo.allocated_to,
				todo.assigned_by,
				todo.custom_created_by
			FROM `tabToDo` todo
			WHERE todo.status = 'Closed'
				AND todo.custom_closed_on >= %s
				AND {user_scope_sql}
			ORDER BY todo.custom_closed_on DESC, todo.modified DESC
			LIMIT %s
		""",
		[cutoff, *user_scope_params, fetch_limit],
		as_dict=True,
	)

	has_more = len(rows) >= fetch_limit
	if has_more:
		rows = rows[:100]

	if not rows:
		return {"items": [], "has_more": False}

	names = [row.name for row in rows]
	assignee_map = get_todo_assignees(names)

	all_users = set()
	for row in rows:
		users = assignee_map.get(row.name) or ([row.allocated_to] if row.allocated_to else [])
		all_users.update(users)

	user_details = {}
	if all_users:
		for u in frappe.get_all(
			"User",
			filters={"name": ("in", list(all_users))},
			fields=_user_fields(include_image=True),
			limit_page_length=0,
		):
			user_details[u.name] = u

	items = []
	for row in rows:
		serialized = _serialize_focus_row(row, today, today, today, assignee_map, user_details)
		serialized["urgency_band"] = "closed"
		items.append(serialized)

	return {"items": items, "has_more": has_more}


@frappe.whitelist()
def search_flow_hub_todos(query):
	query = (query or "").strip()
	if len(query) < 2:
		return []

	user_scope_sql, user_scope_params = get_user_scope_condition("todo")
	today = getdate(nowdate())
	stale_cutoff  = getdate(add_days(today, -7))
	due_soon_to   = getdate(add_days(today, 3))
	like_query    = f"%{query}%"

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
				todo.modified,
				todo.allocated_to,
				todo.assigned_by,
				todo.custom_created_by
			FROM `tabToDo` todo
			WHERE todo.status IN ('Open', 'In Progress')
				AND (todo.custom_title LIKE %s OR todo.description LIKE %s)
				AND {user_scope_sql}
			ORDER BY todo.modified DESC
			LIMIT 15
		""",
		[like_query, like_query, *user_scope_params],
		as_dict=True,
	)

	if not rows:
		return []

	names = [row.name for row in rows]
	assignee_map = get_todo_assignees(names)

	all_users = set()
	for row in rows:
		users = assignee_map.get(row.name) or ([row.allocated_to] if row.allocated_to else [])
		all_users.update(users)

	user_details = {}
	if all_users:
		for u in frappe.get_all(
			"User",
			filters={"name": ("in", list(all_users))},
			fields=_user_fields(include_image=True),
			limit_page_length=0,
		):
			user_details[u.name] = u

	return [
		_serialize_focus_row(row, today, stale_cutoff, due_soon_to, assignee_map, user_details)
		for row in rows
	]


def get_default_action_queue_statuses(filters=None) -> list[str]:
	parsed = parse_filters(filters)
	statuses = parse_multi_select(parsed.get("status"))
	if statuses:
		return statuses
	return list(ACTIVE_STATUSES)


def _get_aggregated_user_metrics(
	today: date,
	due_soon_from: date,
	due_soon_to: date,
	stale_cutoff: date,
) -> dict:
	"""Single CASE WHEN aggregation for all count metrics."""
	user_scope_sql, user_scope_params = get_user_scope_condition("todo")
	modified_expr = _date_expr("todo.modified")

	row = frappe.db.sql(
		f"""
			SELECT
				COUNT(CASE WHEN todo.status IN ('Open','In Progress')
				           AND todo.date IS NOT NULL AND todo.date < %s THEN 1 END) AS overdue,
				COUNT(CASE WHEN todo.status IN ('Open','In Progress')
				           AND todo.date = %s THEN 1 END) AS due_today,
				COUNT(CASE WHEN todo.status IN ('Open','In Progress')
				           AND todo.date BETWEEN %s AND %s THEN 1 END) AS due_soon,
				COUNT(CASE WHEN todo.status = 'In Progress' THEN 1 END) AS in_progress,
				COUNT(CASE WHEN todo.status = 'In Progress'
				           AND {modified_expr} <= %s THEN 1 END) AS stale,
				COUNT(CASE WHEN todo.status IN ('Open','In Progress') THEN 1 END) AS active_total,
				COUNT(CASE WHEN todo.status IN ('Open','In Progress')
				           AND todo.date IS NULL THEN 1 END) AS no_due_date,
				COUNT(CASE WHEN todo.status IN ('Open','In Progress')
				           AND todo.priority IN ('Urgent','High') THEN 1 END) AS hp_active
			FROM `tabToDo` todo
			WHERE {user_scope_sql}
		""",
		[today, today, due_soon_from, due_soon_to, stale_cutoff, *user_scope_params],
		as_dict=True,
	)

	result = row[0] if row else {}
	return {
		"overdue": cint(result.get("overdue") or 0),
		"due_today": cint(result.get("due_today") or 0),
		"due_soon": cint(result.get("due_soon") or 0),
		"in_progress": cint(result.get("in_progress") or 0),
		"stale": cint(result.get("stale") or 0),
		"active_total": cint(result.get("active_total") or 0),
		"no_due_date": cint(result.get("no_due_date") or 0),
		"high_priority": cint(result.get("hp_active") or 0),
	}


def _get_closed_today(today: date) -> int:
	user_scope_sql, user_scope_params = get_user_scope_condition("todo")
	closed_on_expr = _date_expr("todo.custom_closed_on")
	rows = frappe.db.sql(
		f"""
			SELECT COUNT(*) AS cnt
			FROM `tabToDo` todo
			WHERE todo.status IN ('Closed', 'Cancelled')
			  AND {closed_on_expr} = %s
			  AND {user_scope_sql}
		""",
		[today, *user_scope_params],
		as_dict=True,
	)
	return cint((rows[0] if rows else {}).get("cnt") or 0)


def _build_attention_message(closed_today: int) -> str:
	if closed_today == 0:
		first_name = (
			frappe.db.get_value("User", frappe.session.user, "first_name") or ""
		).strip() or frappe.session.user.split("@")[0]
		return _("Welcome, {0}").format(first_name)

	return _("{0} closed · keep it up").format(closed_today)


def _get_focus_queue(limit: int, stale_cutoff: date, due_soon_cutoff: date) -> list[dict]:
	user_scope_sql, user_scope_params = get_user_scope_condition("todo")
	today = getdate(nowdate())

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
				todo.modified,
				todo.allocated_to,
				todo.assigned_by,
				todo.custom_created_by
			FROM `tabToDo` todo
			WHERE todo.status IN ('Open', 'In Progress')
				AND {user_scope_sql}
			ORDER BY
				CASE
					WHEN todo.date IS NOT NULL AND todo.date < %s
					     AND todo.priority IN ('Urgent','High') THEN 0
					WHEN todo.date IS NOT NULL AND todo.date < %s THEN 1
					WHEN todo.date = %s AND todo.priority IN ('Urgent','High') THEN 2
					WHEN todo.date = %s THEN 3
					ELSE 4
				END,
				CASE WHEN todo.date IS NULL THEN 1 ELSE 0 END,
				todo.date ASC,
				todo.modified ASC
			LIMIT %s
		""",
		[*user_scope_params, today, today, today, today, limit],
		as_dict=True,
	)

	if not rows:
		return []

	names = [row.name for row in rows]
	assignee_map = get_todo_assignees(names)

	all_users = set()
	for row in rows:
		users = assignee_map.get(row.name) or ([row.allocated_to] if row.allocated_to else [])
		all_users.update(users)

	user_details = {}
	if all_users:
		for u in frappe.get_all(
			"User",
			filters={"name": ("in", list(all_users))},
			fields=_user_fields(include_image=True),
			limit_page_length=0,
		):
			user_details[u.name] = u

	return [
		_serialize_focus_row(row, today, stale_cutoff, due_soon_cutoff, assignee_map, user_details)
		for row in rows
	]


def _serialize_focus_row(
	row, today: date, stale_cutoff: date, due_soon_cutoff: date, assignee_map: dict = None, user_details: dict = None
) -> dict:
	name = _to_text(_get_value(row, "name"))
	priority = _to_text(_get_value(row, "priority"))
	status = _to_text(_get_value(row, "status"))
	due_date = _to_date(_get_value(row, "date"))
	modified_date = _to_date(_get_value(row, "modified"))

	if due_date and due_date < today:
		urgency_band = "overdue"
	elif due_date and due_date == today:
		urgency_band = "due_today"
	elif status == "In Progress" and modified_date and modified_date <= stale_cutoff:
		urgency_band = "stale"
	elif due_date and due_date <= due_soon_cutoff:
		urgency_band = "due_soon"
	else:
		urgency_band = "active"

	assignees = []
	if assignee_map is not None:
		allocated_to = _to_text(_get_value(row, "allocated_to"))
		assigned_by = _to_text(_get_value(row, "assigned_by"))
		custom_created_by = _to_text(_get_value(row, "custom_created_by"))
		users = assignee_map.get(name) or ([allocated_to] if allocated_to else [])
		details = user_details or {}
		for i, user_id in enumerate(users):
			u = details.get(user_id)
			full_name = _user_display_name(u) or user_id
			initials = _get_initials(full_name)
			roles = []
			if user_id == custom_created_by:
				roles.append(_("Creator"))
			if user_id == assigned_by:
				roles.append(_("Owner"))
			if i == 0:
				roles.append(_("Main Assignee"))
			else:
				roles.append(_("Assignee"))
			assignees.append(
				{
					"user": user_id,
					"full_name": full_name,
					"initials": initials,
					"image": (u.user_image if u else "") or "",
					"roles": roles,
				}
			)

	return {
		"name": name,
		"title": get_todo_title(row) or name,
		"status": status,
		"modified": cstr(_get_value(row, "modified")),
		"priority": priority,
		"is_high_priority": priority in HIGH_PRIORITY_VALUES,
		"due_date": str(due_date) if due_date else "",
		"due_label": get_due_date_context(row),
		"urgency_band": urgency_band,
		"assignees": assignees,
		"description": cstr(_get_value(row, "description") or ""),
	}


def _get_todo_tags(todo_names: list[str]) -> dict[str, list[str]]:
	if not todo_names:
		return {}

	rows = frappe.get_all(
		"Tag Link",
		filters={"document_type": "ToDo", "document_name": ("in", todo_names)},
		fields=["document_name", "tag"],
		order_by="creation asc",
		limit_page_length=0,
	)

	tag_map: dict[str, list[str]] = defaultdict(list)
	for row in rows:
		tag_name = cstr(row.tag).strip()
		if tag_name and tag_name not in tag_map[row.document_name]:
			tag_map[row.document_name].append(tag_name)

	return tag_map


def _get_todo_attachments(todo_name: str) -> list[dict]:
	rows = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "ToDo", "attached_to_name": todo_name},
		fields=["name", "file_name", "file_url", "is_private", "owner", "creation"],
		order_by="creation desc",
		limit_page_length=30,
	)

	return [
		{
			"name": cstr(row.name),
			"file_name": cstr(row.file_name),
			"file_url": cstr(row.file_url),
			"is_private": cint(row.is_private),
			"owner": cstr(row.owner),
			"creation": cstr(row.creation),
		}
		for row in rows
	]


def _get_todo_activity(todo_name: str) -> list[dict]:
	rows = frappe.get_all(
		"Comment",
		filters={"reference_doctype": "ToDo", "reference_name": todo_name},
		fields=["name", "comment_type", "comment_by", "comment_email", "content", "owner", "creation"],
		order_by="creation desc",
		limit_page_length=40,
	)

	activity = []
	for row in rows:
		activity.append(
			{
				"name": cstr(row.name),
				"type": cstr(row.comment_type or "Comment"),
				"by": cstr(row.comment_by or row.comment_email or row.owner),
				"content": extract_plain_text(row.content) or _("No details"),
				"creation": cstr(row.creation),
			}
		)

	return activity


def _get_todo_detail_field_values(doc) -> dict[str, str]:
	values = {}
	for fieldname in FLOW_HUB_DETAIL_FIELDNAMES:
		value = cstr(doc.get(fieldname) or "").strip()
		if value:
			values[fieldname] = value
	return values


def _user_display_name(user_record) -> str:
	"""Return custom_short_name when available, falling back to full_name."""
	if not user_record:
		return ""
	short = cstr(getattr(user_record, "custom_short_name", "") or "")
	if short:
		return short
	return cstr(user_record.full_name or user_record.name or "")


def _user_fields(include_image: bool = True) -> list:
	"""User fields to fetch; adds custom_short_name when reyal_core is installed."""
	fields = ["name", "full_name"]
	if include_image:
		fields.append("user_image")
	if "reyal_core" in frappe.get_installed_apps():
		fields.append("custom_short_name")
	return fields


def _get_initials(full_name: str) -> str:
	parts = (full_name or "").strip().split()
	if not parts:
		return "?"
	if len(parts) == 1:
		return parts[0][0].upper()
	return (parts[0][0] + parts[-1][0]).upper()


def _get_unassigned_active_count() -> int:
	"""Org-wide count of active ToDos with no assignee at all."""
	count = frappe.db.sql(
		"""
			SELECT COUNT(DISTINCT todo.name)
			FROM `tabToDo` todo
			WHERE todo.status IN ('Open', 'In Progress')
				AND (todo.allocated_to IS NULL OR todo.allocated_to = '')
				AND NOT EXISTS (
					SELECT 1
					FROM `tabToDo Assignee` assignee_row
					WHERE assignee_row.parent = todo.name
						AND assignee_row.parenttype = 'ToDo'
				)
		"""
	)[0][0]
	return cint(count or 0)


def _get_throughput_30d() -> dict:
	today = getdate(nowdate())
	period_from = getdate(add_days(today, -29))
	prev_to = getdate(add_days(today, -30))
	prev_from = getdate(add_days(today, -59))

	user_scope_sql, user_scope_params = get_user_scope_condition("todo")
	creation_expr = _date_expr("todo.creation")
	closed_on_expr = _date_expr("todo.custom_closed_on")
	cancelled_on_expr = _date_expr("todo.custom_cancelled_on")

	row = frappe.db.sql(
		f"""
			SELECT
				COUNT(CASE WHEN {creation_expr} BETWEEN %s AND %s THEN 1 END) AS created,
				COUNT(CASE WHEN todo.status = 'Closed'
				           AND {closed_on_expr} BETWEEN %s AND %s THEN 1 END) AS closed,
				COUNT(CASE WHEN todo.status = 'Cancelled'
				           AND {cancelled_on_expr} BETWEEN %s AND %s THEN 1 END) AS cancelled,
				COUNT(CASE WHEN {creation_expr} BETWEEN %s AND %s THEN 1 END) AS prev_created,
				COUNT(CASE WHEN todo.status = 'Closed'
				           AND {closed_on_expr} BETWEEN %s AND %s THEN 1 END) AS prev_closed,
				COUNT(CASE WHEN todo.status = 'Cancelled'
				           AND {cancelled_on_expr} BETWEEN %s AND %s THEN 1 END) AS prev_cancelled
			FROM `tabToDo` todo
			WHERE {user_scope_sql}
		""",
		[
			period_from, today, period_from, today, period_from, today,
			prev_from, prev_to, prev_from, prev_to, prev_from, prev_to,
			*user_scope_params,
		],
		as_dict=True,
	)

	result = row[0] if row else {}
	created = cint(result.get("created") or 0)
	closed = cint(result.get("closed") or 0) + cint(result.get("cancelled") or 0)
	prev_created = cint(result.get("prev_created") or 0)
	prev_closed = cint(result.get("prev_closed") or 0) + cint(result.get("prev_cancelled") or 0)

	net = closed - created
	prev_net = prev_closed - prev_created

	if net > prev_net:
		trend = "improving"
	elif net < prev_net:
		trend = "worsening"
	else:
		trend = "stable"

	return {
		"created": created,
		"closed": closed,
		"net": net,
		"prev_net": prev_net,
		"trend": trend,
		"daily_closed": _get_daily_closed(period_from, today, user_scope_sql, user_scope_params),
	}


def _get_daily_closed(from_date: date, to_date: date, user_scope_sql: str, user_scope_params: list) -> list[int]:
	closed_expr = _date_expr("todo.custom_closed_on")
	cancelled_expr = _date_expr("todo.custom_cancelled_on")

	rows = frappe.db.sql(
		f"""
			SELECT day_val, SUM(cnt) AS total
			FROM (
				SELECT {closed_expr} AS day_val, COUNT(*) AS cnt
				FROM `tabToDo` todo
				WHERE todo.status = 'Closed'
					AND {closed_expr} BETWEEN %s AND %s
					AND {user_scope_sql}
				GROUP BY {closed_expr}
				UNION ALL
				SELECT {cancelled_expr} AS day_val, COUNT(*) AS cnt
				FROM `tabToDo` todo
				WHERE todo.status = 'Cancelled'
					AND {cancelled_expr} BETWEEN %s AND %s
					AND {user_scope_sql}
				GROUP BY {cancelled_expr}
			) sub
			GROUP BY day_val
			ORDER BY day_val
		""",
		[from_date, to_date, *user_scope_params, from_date, to_date, *user_scope_params],
		as_dict=True,
	)

	day_map = {str(_to_date(r.day_val) or ""): cint(r.total) for r in rows if r.day_val}
	n = (to_date - from_date).days + 1
	return [day_map.get(str(getdate(add_days(str(from_date), i))), 0) for i in range(n)]


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

	user_scope_sql, user_scope_params = get_user_scope_condition("todo")
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


def get_user_scope_condition(alias: str = "todo") -> tuple[str, list[str]]:
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
		)
		AND ({alias}.custom_is_group_child IS NULL OR {alias}.custom_is_group_child = 0)""",
		[current_user, current_user, current_user],
	)
