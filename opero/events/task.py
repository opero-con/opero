"""Task event handlers ported from FC Server Scripts."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

from opero import entity
from opero.opero.doctype.task_allocation.task_allocation import (
	get_budget_usage,
	get_overrun,
	update_project_allocated_hours,
)


def before_insert_task(doc, _method=None):
	_restrict_non_pm_create(doc)


def validate_task(doc, _method=None):
	_validate_one_budget_row_per_person(doc)
	_sync_budget_days(doc)
	_update_budget_usage(doc)


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


def _validate_one_budget_row_per_person(doc):
	people = set()
	for row in doc.get("custom_time_allocation") or []:
		if row.personnel in people:
			frappe.throw(_("{0} has more than one Hours Budget row.").format(row.personnel))
		people.add(row.personnel)


def _sync_budget_days(doc):
	"""Budget Hours is stored; Budget Days follows it at the standard working day."""
	standard_hours = flt(frappe.db.get_single_value("HR Settings", "standard_working_hours"))
	if not standard_hours:
		return
	for row in doc.get("custom_time_allocation") or []:
		row.days = flt(flt(row.hours) / standard_hours, 2)


def _update_budget_usage(doc):
	"""Committed and overrun follow the allocations; people with allocations keep their row."""
	if doc.is_new():
		return
	usage = get_budget_usage(doc.name)
	rows = {row.personnel: row for row in doc.get("custom_time_allocation") or []}
	missing = [
		row.personnel_name or employee
		for employee, row in usage.items()
		if flt(row.hours) and employee not in rows
	]
	if missing:
		frappe.throw(
			_("Keep the Hours Budget rows of people with submitted allocations: {0}").format(
				", ".join(missing)
			),
			title=_("Budget row needed"),
		)
	for personnel, row in rows.items():
		used = usage.get(personnel) or frappe._dict(hours=0)
		row.committed = flt(used.hours)
		row.overrun = get_overrun(used.hours, row.hours)


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
