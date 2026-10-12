from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime

import frappe
from frappe import _
from frappe.utils import add_days, cstr, date_diff, getdate, nowdate
from frappe.utils.data import strip_html
from frappe.utils.html_utils import unescape_html

from opero import entity

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
	title = extract_plain_text(
		getattr(row, "custom_title", None) if hasattr(row, "custom_title") else row.get("custom_title")
	)
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


def _entity_reference_sources() -> dict[str, str]:
	"""Referenced DocTypes a ToDo can inherit an entity from -> their company field."""
	sources = {"Project": "company"}
	for doctype, scope in entity.active_project_scopes().items():
		if frappe.get_meta(doctype).has_field(scope.company_field):
			sources[doctype] = scope.company_field
	return sources


def get_entity_condition(filters=None, alias: str = "todo") -> tuple[str, list]:
	"""SQL narrowing ToDos by entity, resolved through the document they reference.

	Applies the optional Company **filter** only: keeps ToDos that resolve to that
	entity. A ToDo carries no company of its own; one referencing nothing, or
	something that is not entity-scoped, has no entity and is only excluded by an
	explicit filter.
	"""
	clauses = []
	params: list[str] = []

	company = _to_text(parse_filters(filters).get("company"))
	if company:
		matches, match_params = _reference_entity_clause(alias, [company])
		clauses.append(matches)
		params.extend(match_params)

	return (" AND ".join(clauses), params) if clauses else ("", [])


def _reference_entity_clause(alias: str, companies: list[str], exclude: bool = False) -> tuple[str, list]:
	"""Match — or rule out — ToDos whose reference resolves to one of `companies`.

	`exclude=True` remains for callers that need a negative match; entity-less
	ToDos are left untouched by `NOT IN`.
	"""
	placeholders = ", ".join(["%s"] * len(companies))
	joiner = " AND " if exclude else " OR "

	clauses = []
	params: list[str] = []
	for doctype, company_field in _entity_reference_sources().items():
		match = (
			f"{alias}.reference_type = %s AND {alias}.reference_name IN"
			f" (SELECT name FROM `tab{doctype}`"
			f" WHERE `{company_field}` {'NOT IN' if exclude else 'IN'} ({placeholders}))"
		)
		clauses.append(f"NOT ({match})" if exclude else f"({match})")
		params.append(doctype)
		params.extend(companies)

	return "(" + joiner.join(clauses) + ")", params


def get_todo_entities(rows: list) -> dict[str, str]:
	"""Map each row's ToDo name to the entity of the document it references."""
	wanted: dict[str, list[str]] = defaultdict(list)
	for row in rows:
		reference_type = _to_text(row.get("reference_type"))
		reference_name = _to_text(row.get("reference_name"))
		if reference_type and reference_name:
			wanted[reference_type].append(reference_name)

	sources = _entity_reference_sources()
	entities: dict[str, str] = {}
	for reference_type, names in wanted.items():
		company_field = sources.get(reference_type)
		if not company_field:
			continue
		for record in frappe.get_all(
			reference_type,
			filters={"name": ("in", list(set(names)))},
			fields=["name", f"{company_field} as company"],
			limit_page_length=0,
		):
			entities[f"{reference_type}:{record.name}"] = record.company

	return {
		row.get("todo") or row.get("name"): entities.get(
			f"{_to_text(row.get('reference_type'))}:{_to_text(row.get('reference_name'))}", ""
		)
		for row in rows
	}


def get_default_action_queue_statuses(filters=None) -> list[str]:
	parsed = parse_filters(filters)
	statuses = parse_multi_select(parsed.get("status"))
	if statuses:
		return statuses
	return list(ACTIVE_STATUSES)


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


def get_user_scope_condition(alias: str = "todo") -> tuple[str, list[str]]:
	current_user = frappe.session.user
	from opero.todo_enhancements import _has_unrestricted_todo_access

	if _has_unrestricted_todo_access(current_user, "read"):
		return "1 = 1", []

	return (
		f"""(
			{alias}.owner = %s
			OR {alias}.allocated_to = %s
			OR {alias}.assigned_by = %s
			OR EXISTS (
				SELECT 1
				FROM `tabToDo Assignee` assignee_row
				WHERE assignee_row.parent = {alias}.name
					AND assignee_row.parenttype = 'ToDo'
					AND assignee_row.user = %s
			)
		)
		AND ({alias}.custom_is_group_child IS NULL OR {alias}.custom_is_group_child = 0)""",
		[current_user, current_user, current_user, current_user],
	)
