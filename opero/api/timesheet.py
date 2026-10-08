"""Permission-aware timesheet totals."""

import frappe


@frappe.whitelist()
def get_total_spent_hours(employee, project):
	frappe.get_doc("Project", project).check_permission("read")
	frappe.get_doc("Employee", employee).check_permission("read")
	rows = frappe.get_list(
		"Timesheet",
		filters={"employee": employee, "parent_project": project, "docstatus": 1},
		fields=["sum(total_hours) as hours"],
		limit_page_length=1,
	)
	return float(rows[0].hours or 0) if rows else 0


@frappe.whitelist()
def get_allocation_balances(employee, project=None, time_logs=None, timesheet_name=None):
	from frappe.utils import get_datetime

	from opero.events.timesheet import get_monthly_balances

	if project:
		frappe.get_doc("Project", project).check_permission("read")
	frappe.get_doc("Employee", employee).check_permission("read")
	if timesheet_name and frappe.db.exists("Timesheet", timesheet_name):
		frappe.get_doc("Timesheet", timesheet_name).check_permission("read")
	rows = [
		frappe._dict(row) for row in frappe.parse_json(time_logs) if row.get("task") and row.get("from_time")
	]
	if not rows:
		return []
	tasks = {row.task for row in rows}
	filters = {"name": ["in", list(tasks)]}
	if project:
		filters["project"] = project
	visible = frappe.get_list(
		"Task",
		filters=filters,
		fields=["name", "subject"],
		limit_page_length=0,
	)
	task_names = {row.name: row.subject or row.name for row in visible}
	if tasks != set(task_names):
		frappe.throw(
			"Every task must be accessible and belong to the selected project.", frappe.PermissionError
		)
	allocation, usage = get_monthly_balances(employee, rows, timesheet_name)
	current = {}
	for row in rows:
		key = (row.task, get_datetime(row.from_time).strftime("%b %Y"))
		current[key] = current.get(key, 0) + float(row.get("hours") or 0)
	return [
		dict(
			task=task,
			task_name=task_names[task],
			month=month,
			allocated=allocation.get((task, month), 0),
			submitted=usage.get((task, month), 0),
			current=hours,
			remaining=allocation.get((task, month), 0) - usage.get((task, month), 0) - hours,
		)
		for (task, month), hours in sorted(current.items())
	]


@frappe.whitelist()
def preview_daily_times(employee, time_logs, timesheet_name=None):
	"""Preview the save-time schedule without writing or saving a document."""
	from opero.events.timesheet import generate_daily_times

	frappe.get_doc("Employee", employee).check_permission("read")
	if timesheet_name and frappe.db.exists("Timesheet", timesheet_name):
		existing = frappe.get_doc("Timesheet", timesheet_name)
		existing.check_permission("write")
		if existing.docstatus != 0:
			frappe.throw("Only unapproved timesheets can be rescheduled.")
	else:
		frappe.has_permission("Timesheet", "create", throw=True)
		timesheet_name = None
	rows = frappe.parse_json(time_logs)
	if not isinstance(rows, list):
		frappe.throw("Time entries must be a list.")
	complete = [row for row in rows if row.get("from_time") and float(row.get("hours") or 0) > 0]
	if not complete:
		return []
	doc = frappe.get_doc({"doctype": "Timesheet", "employee": employee, "time_logs": complete})
	doc.name = timesheet_name
	generate_daily_times(doc)
	return [
		{"name": source.get("name"), "from_time": str(row.from_time), "to_time": str(row.to_time)}
		for source, row in zip(complete, doc.time_logs, strict=True)
	]
