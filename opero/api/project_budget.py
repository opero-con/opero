"""Project Budget API methods."""

from __future__ import annotations

import frappe


@frappe.whitelist()
def get_timesheet_actuals(project: str | None = None):
	project = project or frappe.form_dict.get("project")
	if not project:
		frappe.throw("Project is required")

	result = frappe.db.sql(
		"""
		SELECT SUM(total_billable_amount) AS actual
		FROM `tabTimesheet`
		WHERE parent_project = %s AND docstatus = 1
		""",
		(project,),
		as_dict=True,
	)
	actual = float((result[0].actual if result else 0) or 0)
	return {"Timesheets - OS": actual}
