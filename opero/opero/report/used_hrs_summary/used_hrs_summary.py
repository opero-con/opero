# Copyright (c) 2026, Patrick Willy and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, getdate


def execute(filters=None):
	filters = filters or {}
	year = cint(filters.get("year") or getdate().year)
	project = filters.get("project") or None

	columns = [
		{
			"fieldname": "contributor",
			"label": _("Contributor"),
			"fieldtype": "Data",
			"width": 220,
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

	data = frappe.db.sql(
		"""
		SELECT
			ts.employee_name AS contributor,
			ts.parent_project AS project,
			MONTHNAME(ts.start_date) AS month,
			SUM(tl.hours) AS posted_hrs
		FROM `tabTimesheet` ts
		JOIN `tabTimesheet Detail` tl ON ts.name = tl.parent
		WHERE YEAR(ts.start_date) = %(year)s
		  AND (%(project)s IS NULL OR ts.parent_project = %(project)s)
		GROUP BY
			ts.employee_name,
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
		{"year": year, "project": project},
		as_dict=True,
	)

	return columns, data
