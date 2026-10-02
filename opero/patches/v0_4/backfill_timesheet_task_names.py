"""Fill Timesheet Detail's Task Name from the task for rows saved before the field was fetched."""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.has_column("Timesheet Detail", "custom_project_task"):
		return

	frappe.db.sql(
		"""
		UPDATE `tabTimesheet Detail` detail
		JOIN `tabTask` task ON task.name = detail.task
		SET detail.custom_project_task = task.subject
		WHERE IFNULL(detail.custom_project_task, '') = ''
		"""
	)
