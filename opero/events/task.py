"""Task event handlers ported from FC Server Scripts."""

from __future__ import annotations

import frappe


def before_insert_task(doc, _method=None):
	_restrict_non_pm_create(doc)


def on_update_task(doc, _method=None):
	_sum_allocated_hours_on_project(doc)
	_sync_task_time_distributions(doc)
	_push_task_dates_to_ttd(doc)


def after_insert_task(doc, _method=None):
	_push_task_dates_to_ttd(doc)


def _restrict_non_pm_create(doc):
	if not doc.project:
		return
	project_manager = frappe.db.get_value("Project", doc.project, "custom_pm_name")
	if not project_manager:
		return
	personnel_name = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "employee_name")
	if personnel_name and personnel_name != project_manager:
		frappe.throw(f"Please contact the PM, {project_manager}, for Task creation in this Project")


def _sum_allocated_hours_on_project(doc):
	if not doc.project:
		return
	standard_working_hours = frappe.db.get_single_value("HR Settings", "standard_working_hours") or 8
	total_days = (
		frappe.db.sql(
			"SELECT SUM(custom_total_days) FROM `tabTask` WHERE project = %s",
			(doc.project,),
		)[0][0]
		or 0
	)
	frappe.db.set_value(
		"Project",
		doc.project,
		"custom_allocated_hours",
		float(total_days) * float(standard_working_hours),
		update_modified=False,
	)


def _sync_task_time_distributions(doc):
	if not doc.subject:
		return
	try:
		personnel_rows = [
			{"personnel": row.personnel, "days": row.days, "hours": row.hours}
			for row in (doc.custom_time_allocation or [])
			if row.personnel
		]
		existing = frappe.db.sql(
			"""
			SELECT name, personnel, days_allocated, hours_allocated
			FROM `tabTask Time Distribution`
			WHERE project_task = %s
			""",
			(doc.name,),
			as_dict=True,
		)
		by_personnel = {row.personnel: row for row in existing}

		for person in personnel_rows:
			match = by_personnel.get(person["personnel"])
			if match:
				frappe.db.set_value(
					"Task Time Distribution",
					match.name,
					{"days_allocated": person["days"], "hours_allocated": person["hours"]},
					update_modified=False,
				)
			elif doc.status not in ("Completed", "Cancelled"):
				frappe.get_doc(
					{
						"doctype": "Task Time Distribution",
						"project_task": doc.name,
						"personnel": person["personnel"],
						"days_allocated": person["days"],
						"hours_allocated": person["hours"],
					}
				).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Task Time Distribution Update Error")


def _push_task_dates_to_ttd(doc):
	"""Keep Task Time Distribution date fields in sync with Task dates.

	FC scripts incorrectly filtered on `parent`; Task Time Distribution links via `project_task`.
	"""
	if doc.exp_end_date is not None:
		frappe.db.sql(
			"""
			UPDATE `tabTask Time Distribution`
			SET task_end = %s
			WHERE project_task = %s
			""",
			(doc.exp_end_date, doc.name),
		)
	if doc.exp_start_date is not None:
		frappe.db.sql(
			"""
			UPDATE `tabTask Time Distribution`
			SET task_start = %s
			WHERE project_task = %s
			""",
			(doc.exp_start_date, doc.name),
		)
