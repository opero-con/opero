# Copyright (c) 2026, Patrick Willy and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	months = frappe.db.sql(
		"""
		SELECT DISTINCT MONTH(tsd.from_time) AS month, MONTHNAME(tsd.from_time) AS month_name
		FROM `tabTimesheet Detail` tsd
		WHERE tsd.from_time IS NOT NULL
		ORDER BY MONTH(tsd.from_time)
		""",
		as_dict=True,
	)

	columns = [
		{
			"fieldname": "task_subject",
			"label": _("Task Subject"),
			"fieldtype": "Data",
			"width": 220,
		}
	]
	month_selects = []
	for month in months:
		fieldname = f"month_{int(month.month)}"
		columns.append(
			{
				"fieldname": fieldname,
				"label": _(month.month_name),
				"fieldtype": "Float",
				"width": 110,
			}
		)
		month_selects.append(
			f'SUM(CASE WHEN MONTH(tsd.from_time) = {int(month.month)} THEN tsd.hours ELSE 0 END) AS `{fieldname}`'
		)

	if not month_selects:
		return columns, []

	month_columns_sql = ", ".join(month_selects)
	conditions = []
	values = {}
	if filters.get("project"):
		conditions.append("t.project = %(project)s")
		values["project"] = filters["project"]
	if filters.get("from_date"):
		conditions.append("DATE(tsd.from_time) >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("DATE(tsd.from_time) <= %(to_date)s")
		values["to_date"] = filters["to_date"]

	where_sql = (" AND " + " AND ".join(conditions)) if conditions else ""

	data = frappe.db.sql(
		f"""
		SELECT
			t.subject AS task_subject,
			{month_columns_sql}
		FROM `tabTask` t
		LEFT JOIN `tabTimesheet Detail` tsd ON tsd.task = t.name
		LEFT JOIN `tabTimesheet` ts ON ts.name = tsd.parent
		WHERE 1=1 {where_sql}
		GROUP BY t.name, t.subject
		ORDER BY t.subject
		""",
		values,
		as_dict=True,
	)

	return columns, data
