# Copyright (c) 2026, Patrick Willy and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, getdate

from opero.opero.report.timesheet_permissions import match_conditions


def execute(filters=None):
	filters = filters or {}
	year = cint(filters.get("year") or getdate().year)
	project = filters.get("project") or None
	company = filters.get("company") or None

	columns = [
		{
			"fieldname": "contributor",
			"label": _("Contributor"),
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
		{
			"fieldname": "project",
			"label": _("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 180,
		},
		{
			"fieldname": "month",
			"label": _("Month"),
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "posted_hrs",
			"label": _("Posted Hrs"),
			"fieldtype": "Float",
			"width": 120,
		},
	]

	values = {
		"start": getdate(f"{year}-01-01"),
		"end": getdate(f"{year + 1}-01-01"),
		"project": project,
		"company": company,
	}
	permissions = match_conditions("Timesheet", "ts")
	permissions += match_conditions("Project", "project")

	data = frappe.db.sql(
		f"""
		SELECT
			ts.employee_name AS contributor,
			project.company AS company,
			ts.parent_project AS project,
			MONTHNAME(tl.from_time) AS month,
			SUM(tl.hours) AS posted_hrs
		FROM `tabTimesheet` ts
		JOIN `tabTimesheet Detail` tl ON ts.name = tl.parent
		LEFT JOIN `tabProject` project ON project.name = ts.parent_project
		WHERE ts.docstatus = 1 AND tl.from_time >= %(start)s AND tl.from_time < %(end)s
		  AND (%(project)s IS NULL OR ts.parent_project = %(project)s)
		  AND (%(company)s IS NULL OR project.company = %(company)s)
		{permissions}
		GROUP BY
			ts.employee,
			ts.employee_name,
			project.company,
			ts.parent_project,
			MONTH(tl.from_time),
			MONTHNAME(tl.from_time)
		ORDER BY
			FIELD(
				MONTHNAME(tl.from_time),
				'January', 'February', 'March', 'April', 'May', 'June',
				'July', 'August', 'September', 'October', 'November', 'December'
			),
			ts.employee_name
		""",
		values,
		as_dict=True,
	)

	return columns, data
