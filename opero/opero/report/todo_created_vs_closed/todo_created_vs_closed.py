from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_days
from frappe.utils import cint
from frappe.utils import date_diff
from frappe.utils import getdate
from frappe.utils import nowdate

from opero import todo_dashboard


def execute(filters=None):
	filters = todo_dashboard.parse_filters(filters)
	window_days = _get_time_window_days(filters)
	window_label = _get_time_window_label(filters, window_days)
	today = getdate(nowdate())

	# Custom date range takes precedence over the window selector
	if filters.get("from_date") or filters.get("to_date"):
		from_date, to_date = todo_dashboard.get_reporting_window(filters, default_days=window_days)
		window_label = _("Custom Range")
	else:
		to_date = today
		from_date = getdate(add_days(to_date, -(window_days - 1)))

	day_span = max(1, date_diff(to_date, from_date) + 1)
	granularity = _get_granularity(filters, day_span)
	_validate_granularity_limits(granularity, day_span)

	entity_sql, entity_params = todo_dashboard.get_entity_condition(filters)

	created_counts = _get_created_counts(from_date, to_date, entity_sql, entity_params)
	closed_counts = _get_completion_counts(
		from_date, to_date, "Closed", "custom_closed_on", entity_sql, entity_params
	)
	cancelled_counts = _get_completion_counts(
		from_date, to_date, "Cancelled", "custom_cancelled_on", entity_sql, entity_params
	)
	created_bucket = _aggregate_by_bucket(created_counts, granularity)
	closed_bucket = _aggregate_by_bucket(closed_counts, granularity)
	cancelled_bucket = _aggregate_by_bucket(cancelled_counts, granularity)

	data = []
	labels = []
	created_values = []
	completed_values = []

	for bucket_start in _get_bucket_starts(from_date, to_date, granularity):
		created = created_bucket.get(bucket_start, 0)
		closed = closed_bucket.get(bucket_start, 0)
		cancelled = cancelled_bucket.get(bucket_start, 0)
		completed = closed + cancelled
		period_start, period_end = _get_period_window(bucket_start, from_date, to_date, granularity)
		period_label = _get_period_label(period_start, period_end, granularity)

		data.append(
			{
				"date": bucket_start,
				"period": period_label,
				"created_count": created,
				"completed_count": completed,
				"closed_count": closed,
				"cancelled_count": cancelled,
			}
		)
		labels.append(_get_chart_label(period_start, granularity))
		created_values.append(created)
		completed_values.append(completed)

	columns = get_columns(granularity)
	chart = {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Created"), "values": created_values},
				{"name": _("Completed"), "values": completed_values},
			],
		},
		"type": "line",
		"colors": ["#2563EB", "#059669"],
	}

	total_created = sum(created_values)
	total_completed = sum(completed_values)
	report_summary = [
		{"label": _("Created"), "value": total_created, "datatype": "Int"},
		{"label": _("Completed"), "value": total_completed, "datatype": "Int"},
		{"label": _("Net Change"), "value": total_created - total_completed, "datatype": "Int"},
		{"label": _("Window"), "value": window_label, "datatype": "Data"},
	]

	return columns, data, None, chart, report_summary


def get_columns(granularity):
	date_label = _("Date")
	if granularity == "week":
		date_label = _("Week Start")
	elif granularity == "month":
		date_label = _("Month Start")

	return [
		{"fieldname": "date", "label": date_label, "fieldtype": "Date", "width": 120},
		{"fieldname": "period", "label": _("Period"), "fieldtype": "Data", "width": 170},
		{"fieldname": "created_count", "label": _("Created"), "fieldtype": "Int", "width": 110},
		{"fieldname": "completed_count", "label": _("Completed"), "fieldtype": "Int", "width": 110},
		{"fieldname": "closed_count", "label": _("Closed"), "fieldtype": "Int", "width": 100},
		{"fieldname": "cancelled_count", "label": _("Cancelled"), "fieldtype": "Int", "width": 100},
	]


def _get_created_counts(from_date, to_date, entity_sql="", entity_params=None):
	date_expr = _date_expr("todo.creation")
	rows = frappe.db.sql(
		f"""
			SELECT {date_expr} AS day_key, COUNT(*) AS total
			FROM `tabToDo` todo
			WHERE {date_expr} BETWEEN %s AND %s
				{f"AND {entity_sql}" if entity_sql else ""}
			GROUP BY {date_expr}
		""",
		[from_date, to_date, *(entity_params or [])],
		as_dict=True,
	)
	return {getdate(row.day_key): row.total for row in rows}


def _get_completion_counts(from_date, to_date, status, fieldname, entity_sql="", entity_params=None):
	date_expr = _date_expr(f"todo.{fieldname}")
	rows = frappe.db.sql(
		f"""
			SELECT {date_expr} AS day_key, COUNT(*) AS total
			FROM `tabToDo` todo
			WHERE todo.status = %s
				AND todo.{fieldname} IS NOT NULL
				AND {date_expr} BETWEEN %s AND %s
				{f"AND {entity_sql}" if entity_sql else ""}
			GROUP BY {date_expr}
		""",
		[status, from_date, to_date, *(entity_params or [])],
		as_dict=True,
	)
	counts = defaultdict(int)
	for row in rows:
		counts[getdate(row.day_key)] += row.total
	return counts


def _date_expr(fieldname: str) -> str:
	if frappe.db.db_type == "postgres":
		return f"CAST({fieldname} AS DATE)"
	return f"DATE({fieldname})"


def _get_time_window_days(filters) -> int:
	window_map = {
		"last 30 days": 30,
		"last 90 days": 90,
		"last 180 days": 180,
		"last 365 days": 365,
		"last 730 days": 730,
	}
	selected = (filters.get("time_window") or "Last 30 Days").strip().lower()
	if selected in window_map:
		return window_map[selected]
	fallback_days = cint(filters.get("window_days") or 30)
	return min(max(fallback_days, 1), 730)


def _get_time_window_label(filters, window_days: int) -> str:
	window_map = {
		"last 30 days": _("Last 30 Days"),
		"last 90 days": _("Last 90 Days"),
		"last 180 days": _("Last 180 Days"),
		"last 365 days": _("Last 365 Days"),
		"last 730 days": _("Last 730 Days"),
	}
	selected = (filters.get("time_window") or "").strip().lower()
	if selected in window_map:
		return window_map[selected]
	return _("Last {0} Days").format(window_days)


def _get_granularity(filters, day_span: int) -> str:
	granularity = (filters.get("granularity") or "Auto").strip().lower()
	if granularity in ("day", "week", "month"):
		return granularity
	if day_span <= 90:
		return "day"
	if day_span <= 730:
		return "week"
	return "month"


def _validate_granularity_limits(granularity: str, day_span: int) -> None:
	if granularity == "day" and day_span > 180:
		frappe.throw(
			_(
				"Daily view supports up to 180 days. Use Auto, Week, or Month for larger ranges."
			)
		)
	if granularity == "week" and day_span > 3650:
		frappe.throw(_("Weekly view supports up to 10 years. Use Month for larger ranges."))


def _aggregate_by_bucket(day_counts: dict, granularity: str) -> dict:
	bucket_counts = defaultdict(int)
	for day_key, value in day_counts.items():
		bucket_counts[_get_bucket_start(day_key, granularity)] += value
	return bucket_counts


def _get_bucket_starts(from_date, to_date, granularity: str) -> list:
	bucket_starts = []
	cursor = _get_bucket_start(from_date, granularity)
	while cursor <= to_date:
		bucket_starts.append(cursor)
		cursor = _next_bucket_start(cursor, granularity)
	return bucket_starts


def _get_bucket_start(value, granularity: str):
	value = getdate(value)
	if granularity == "day":
		return value
	if granularity == "week":
		return value - timedelta(days=value.weekday())
	return value.replace(day=1)


def _next_bucket_start(value, granularity: str):
	if granularity == "day":
		return getdate(add_days(value, 1))
	if granularity == "week":
		return getdate(add_days(value, 7))
	year = value.year + (1 if value.month == 12 else 0)
	month = 1 if value.month == 12 else value.month + 1
	return value.replace(year=year, month=month, day=1)


def _get_period_window(bucket_start, from_date, to_date, granularity: str):
	if granularity == "day":
		return bucket_start, bucket_start
	if granularity == "week":
		window_start = max(bucket_start, from_date)
		window_end = min(getdate(add_days(bucket_start, 6)), to_date)
		return window_start, window_end
	last_day = monthrange(bucket_start.year, bucket_start.month)[1]
	window_start = max(bucket_start, from_date)
	window_end = min(bucket_start.replace(day=last_day), to_date)
	return window_start, window_end


def _get_period_label(period_start, period_end, granularity: str) -> str:
	if granularity == "day":
		return period_start.strftime("%d %b %Y")
	if granularity == "month":
		return period_start.strftime("%b %Y")
	return f"{period_start.strftime('%d %b %Y')} to {period_end.strftime('%d %b %Y')}"


def _get_chart_label(period_start, granularity: str) -> str:
	if granularity == "day":
		return period_start.strftime("%d %b")
	if granularity == "month":
		return period_start.strftime("%b %y")
	return period_start.strftime("W%V %y")
