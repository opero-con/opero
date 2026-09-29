"""Task event handlers ported from FC Server Scripts."""

from __future__ import annotations

import frappe

from opero import entity
from opero.opero.doctype.task_allocation.task_allocation import update_project_allocated_hours


def before_insert_task(doc, _method=None):
	_restrict_non_pm_create(doc)


def on_update_task(doc, _method=None):
	_move_allocations_with_task(doc)


def _restrict_non_pm_create(doc):
	if not doc.project:
		return
	project_manager = frappe.db.get_value("Project", doc.project, "custom_pm_name")
	if not project_manager:
		return
	personnel_name = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "employee_name")
	if personnel_name and personnel_name != project_manager:
		frappe.throw(f"Please contact the PM, {project_manager}, for Task creation in this Project")


def _move_allocations_with_task(doc):
	"""Keep Task Allocation's project and company on the task's current project."""
	before = doc.get_doc_before_save()
	if not before or before.project == doc.project:
		return
	frappe.db.sql(
		"UPDATE `tabTask Allocation` SET project = %s, company = %s WHERE task = %s",
		(doc.project, entity.get_project_company(doc.project), doc.name),
	)
	for project in {before.project, doc.project} - {None, ""}:
		update_project_allocated_hours(project)
