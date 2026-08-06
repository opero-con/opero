# Copyright (c) 2026, Patrick Willy and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _

from opero import entity


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
		},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 140,
		},
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
	if filters.get("company"):
		conditions.append("project.company = %(company)s")
		values["company"] = filters["company"]

	# Raw SQL never passes through the permission layer, so the user's Company
	# User Permissions have to be applied here. A task with no project has no
	# entity to be forbidden, so it stays visible.
	permitted = entity.get_permitted_companies()
	if permitted:
		names = ", ".join(f"%(permitted_{i})s" for i in range(len(permitted)))
		conditions.append(f"(project.company IS NULL OR project.company IN ({names}))")
		values.update({f"permitted_{i}": company for i, company in enumerate(permitted)})
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
			project.company AS company,
			{month_columns_sql}
		FROM `tabTask` t
		LEFT JOIN `tabProject` project ON project.name = t.project
		LEFT JOIN `tabTimesheet Detail` tsd ON tsd.task = t.name
		LEFT JOIN `tabTimesheet` ts ON ts.name = tsd.parent
		WHERE 1=1 {where_sql}
		GROUP BY t.name, t.subject, project.company
		ORDER BY t.subject
		""",
		values,
		as_dict=True,
	)

	return columns, data
