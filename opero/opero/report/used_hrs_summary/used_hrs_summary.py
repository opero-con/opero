# Copyright (c) 2026, Patrick Willy and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, getdate

from opero import entity


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

	# Raw SQL never passes through the permission layer, so the user's Company
	# User Permissions have to be applied here. A timesheet with no project has
	# no entity to be forbidden, so it stays visible.
	values = {"year": year, "project": project, "company": company}
	permitted = entity.get_permitted_companies()
	permitted_sql = ""
	if permitted:
		names = ", ".join(f"%(permitted_{i})s" for i in range(len(permitted)))
		permitted_sql = f"AND (project.company IS NULL OR project.company IN ({names}))"
		values.update({f"permitted_{i}": company for i, company in enumerate(permitted)})

	data = frappe.db.sql(
		f"""
		SELECT
			ts.employee_name AS contributor,
			project.company AS company,
			ts.parent_project AS project,
			MONTHNAME(ts.start_date) AS month,
			SUM(tl.hours) AS posted_hrs
		FROM `tabTimesheet` ts
		JOIN `tabTimesheet Detail` tl ON ts.name = tl.parent
		LEFT JOIN `tabProject` project ON project.name = ts.parent_project
		WHERE YEAR(ts.start_date) = %(year)s
		  AND (%(project)s IS NULL OR ts.parent_project = %(project)s)
		  AND (%(company)s IS NULL OR project.company = %(company)s)
		  {permitted_sql}
		GROUP BY
			ts.employee_name,
			project.company,
			ts.parent_project,
			MONTH(ts.start_date),
			MONTHNAME(ts.start_date)
		ORDER BY
			FIELD(
				MONTHNAME(ts.start_date),
				'January', 'February', 'March', 'April', 'May', 'June',
				'July', 'August', 'September', 'October', 'November', 'December'
			),
			ts.employee_name
		""",
		values,
		as_dict=True,
	)

	return columns, data
