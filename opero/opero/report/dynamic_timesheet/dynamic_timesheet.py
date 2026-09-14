# Copyright (c) 2026, Patrick Willy and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate

from opero.opero.report.timesheet_permissions import match_conditions


def execute(filters=None):
	filters = filters or {}
	conditions = ["ts.docstatus = 1", "tsd.from_time IS NOT NULL"]
	values = {}
	for field, expression in (("company", "project.company"), ("project", "t.project")):
		if filters.get(field):
			conditions.append(f"{expression} = %({field})s")
			values[field] = filters[field]
	if filters.get("from_date"):
		conditions.append("tsd.from_time >= %(from_date)s")
		values["from_date"] = getdate(filters["from_date"])
	if filters.get("to_date"):
		from frappe.utils import add_days

		conditions.append("tsd.from_time < %(until)s")
		values["until"] = add_days(getdate(filters["to_date"]), 1)
	if (
		filters.get("from_date")
		and filters.get("to_date")
		and getdate(filters["from_date"]) > getdate(filters["to_date"])
	):
		frappe.throw(_("From Date must be on or before To Date"))
	permissions = match_conditions("Timesheet", "ts")
	permissions += match_conditions("Task", "t")
	permissions += match_conditions("Project", "project")
	rows = frappe.db.sql(
		f"""
		SELECT t.name AS task, t.subject AS task_subject, project.company,
		       DATE_FORMAT(tsd.from_time, '%%Y-%%m') AS month, SUM(tsd.hours) AS hours
		FROM `tabTimesheet Detail` tsd
		JOIN `tabTimesheet` ts ON ts.name = tsd.parent
		JOIN `tabTask` t ON t.name = tsd.task
		JOIN `tabProject` project ON project.name = t.project
		WHERE {' AND '.join(conditions)} {permissions}
		GROUP BY t.name, t.subject, project.company, DATE_FORMAT(tsd.from_time, '%%Y-%%m')
		ORDER BY t.subject, t.name, month
		""",
		values,
		as_dict=True,
	)
	months = sorted({row.month for row in rows})
	columns = [
		{"fieldname": "task", "label": _("Task"), "fieldtype": "Link", "options": "Task", "width": 160},
		{"fieldname": "task_subject", "label": _("Task Subject"), "fieldtype": "Data", "width": 220},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 140,
		},
	]
	for month in months:
		columns.append(
			{
				"fieldname": "month_" + month.replace("-", "_"),
				"label": getdate(month + "-01").strftime("%b %Y"),
				"fieldtype": "Float",
				"width": 110,
			}
		)
	data = {}
	for row in rows:
		item = data.setdefault(
			row.task, {"task": row.task, "task_subject": row.task_subject, "company": row.company}
		)
		item["month_" + row.month.replace("-", "_")] = row.hours
	return columns, list(data.values())
