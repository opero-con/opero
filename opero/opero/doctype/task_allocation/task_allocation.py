import re
from datetime import date

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, escape_html, flt, get_first_day, get_last_day, get_link_to_form

from opero.opero.report.weekly_hours.weekly_hours import WeeklyHours

HOURS_TOLERANCE = 0.000001
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


class TaskAllocation(Document):
	"""Planned hours for one employee on one task in one month; only submitted records count."""

	def validate(self):
		self.month_start = get_month_start(self.month, self.year)
		self.project = frappe.db.get_value("Task", self.task, "project")
		if self.docstatus == 1:
			self.validate_budget_row()
			self.warn_over_capacity()
			self.warn_over_budget()

	def on_submit(self):
		if not self.flags.skip_totals:
			update_allocated_totals(self.task)
			update_budget_usage(self.task, self.employee)

	def before_cancel(self):
		self.validate_timesheets_stay_covered()

	def on_cancel(self):
		update_allocated_totals(self.task)
		update_budget_usage(self.task, self.employee)

	def validate_timesheets_stay_covered(self):
		remaining = get_allocated_hours(
			task=self.task, employee=self.employee, month_start=self.month_start, name=("!=", self.name)
		)
		submitted = self.submitted_hours
		if submitted > remaining + HOURS_TOLERANCE:
			frappe.throw(
				_(
					"{0} has submitted {1}h on this task for {2}; cancelling leaves only {3}h allocated. "
					"Submit a replacement allocation first."
				).format(
					self.personnel_name or self.employee, f"{submitted:g}", self.month_label, f"{remaining:g}"
				)
			)

	def warn_over_capacity(self):
		capacity = get_capacity(self.employee, self.month_start, exclude=self.name)
		if capacity["available"] is None:
			return
		total = capacity["allocated"] + flt(self.hours)
		if total > capacity["available"] + HOURS_TOLERANCE:
			frappe.msgprint(
				_(
					"{0} has {1}h available in {2}; allocations across all tasks now total {3}h ({4}h over)."
				).format(
					self.personnel_name or self.employee,
					f"{capacity['available']:g}",
					self.month_label,
					f"{total:g}",
					f"{total - capacity['available']:g}",
				),
				title=_("Over available time"),
				indicator="orange",
			)

	def validate_budget_row(self):
		if not get_budget(self.task, self.employee):
			frappe.throw(
				_("No Hours Budget for {0} on task {1}.").format(
					frappe.bold(self.personnel_name or self.employee),
					get_link_to_form(
						"Task",
						self.task,
						escape_html(frappe.db.get_value("Task", self.task, "subject") or self.task),
					),
				),
				title=_("No task budget"),
			)

	def warn_over_budget(self):
		budget = get_budget(self.task, self.employee)
		total = get_allocated_hours(task=self.task, employee=self.employee, name=("!=", self.name))
		total += flt(self.hours)
		if total <= budget.hours + HOURS_TOLERANCE:
			return
		frappe.msgprint(
			_(
				"{0}'s budget on this task is {1}h; submitted allocations now total {2}h, an overrun of {3}h."
			).format(
				self.personnel_name or self.employee,
				f"{budget.hours:g}",
				f"{total:g}",
				f"{total - budget.hours:g}",
			),
			title=_("Hours overrun"),
			indicator="orange",
		)

	@property
	def month_label(self):
		return f"{self.month} {self.year}"

	@property
	def submitted_hours(self):
		month = get_first_day(self.month_start)
		return flt(
			frappe.db.sql(
				"""
				SELECT SUM(tl.hours)
				FROM `tabTimesheet` ts JOIN `tabTimesheet Detail` tl ON tl.parent = ts.name
				WHERE ts.docstatus = 1 AND ts.employee = %s AND tl.task = %s
				  AND tl.from_time >= %s AND tl.from_time < %s
				""",
				(self.employee, self.task, month, add_months(month, 1)),
			)[0][0]
		)


def update_allocated_totals(task):
	"""Recompute the task's and its project's allocated hours from Task Allocation."""
	project = frappe.db.get_value("Task", task, "project")
	frappe.db.set_value(
		"Task", task, "custom_total_hours", get_allocated_hours(task=task), update_modified=False
	)
	if project:
		update_project_allocated_hours(project)


def update_project_allocated_hours(project):
	frappe.db.set_value(
		"Project",
		project,
		"custom_allocated_hours",
		get_allocated_hours(project=project),
		update_modified=False,
	)


def get_allocated_hours(**filters):
	"""Sum of submitted allocation hours matching the filters."""
	rows = frappe.get_all(
		"Task Allocation", filters={**filters, "docstatus": 1}, fields=["sum(hours) as hours"]
	)
	return flt(rows[0].hours) if rows else 0


def get_budget(task, employee):
	"""The employee's Hours Budget row on the task, or None."""
	rows = frappe.get_all(
		"Task Time Allocation",
		filters={"parent": task, "parenttype": "Task", "personnel": employee},
		fields=["name", "hours", "committed", "overrun"],
		order_by="idx",
	)
	if len(rows) > 1:
		frappe.throw(_("Task {0} has more than one Hours Budget row for {1}.").format(task, employee))
	if not rows:
		return None
	rows[0].hours = flt(rows[0].hours)
	rows[0].overrun = flt(rows[0].overrun)
	return rows[0]


def get_overrun(allocated, budget_hours):
	overrun = flt(allocated) - flt(budget_hours)
	return overrun if overrun > HOURS_TOLERANCE else 0


def get_budget_usage(task):
	"""Submitted allocation hours per employee on the task."""
	rows = frappe.get_all(
		"Task Allocation",
		filters={"task": task, "docstatus": 1},
		fields=["employee", "personnel_name", "sum(hours) as hours"],
		group_by="employee, personnel_name",
	)
	return {row.employee: row for row in rows}


def update_budget_usage(task, employee):
	"""Store the employee's committed hours and overrun on their task budget row.

	Submitting requires a budget row; the migration adds zero-budget rows for existing
	allocations that have none.
	"""
	usage = get_budget_usage(task).get(employee) or frappe._dict(hours=0)
	budget = get_budget(task, employee)
	overrun = get_overrun(usage.hours, budget.hours if budget else 0)
	values = {"committed": flt(usage.hours), "overrun": overrun}
	if budget:
		frappe.db.set_value("Task Time Allocation", budget.name, values)
		return
	if not overrun:
		return
	frappe.get_doc(
		{
			"doctype": "Task Time Allocation",
			"parent": task,
			"parenttype": "Task",
			"parentfield": "custom_time_allocation",
			"idx": frappe.db.count("Task Time Allocation", {"parent": task, "parenttype": "Task"}) + 1,
			"personnel": employee,
			"hours": 0,
			**values,
		}
	).db_insert()


def get_month_start(month, year):
	if not re.fullmatch(r"\d{4}", str(year or "")):
		frappe.throw(_("Year must be four digits, for example 2026."))
	if month not in MONTHS:
		frappe.throw(_("Month must be one of {0}.").format(", ".join(MONTHS)))
	return date(int(year), MONTHS.index(month) + 1, 1)


def get_available_hours(employee, month_start):
	"""Expected hours for the month under the Weekly Hours rules; None when unknown."""
	if not flt(frappe.db.get_single_value("HR Settings", "standard_working_hours")):
		return None
	report = WeeklyHours(
		frappe._dict(employee=employee, from_date=month_start, to_date=get_last_day(month_start))
	)
	person = next((row for row in report.employees if row.name == employee), None)
	hours = [report.get_expected_hours(person, week) for week in report.weeks] if person else [None]
	return None if None in hours else sum(hours)


def get_capacity(employee, month_start, exclude=None):
	"""Available hours and submitted hours across all tasks, leaving out one record."""
	filters = {"employee": employee, "month_start": month_start}
	if exclude:
		filters["name"] = ("!=", exclude)
	return {
		"available": get_available_hours(employee, month_start),
		"allocated": get_allocated_hours(**filters),
	}


def get_same_task_allocations(task, employee, month_start, exclude=None):
	"""Other submitted allocations for the same task, employee, and month."""
	filters = {"task": task, "employee": employee, "month_start": month_start, "docstatus": 1}
	if exclude:
		filters["name"] = ("!=", exclude)
	return frappe.get_all("Task Allocation", filters=filters, fields=["name", "hours"], order_by="creation")


def get_month_fields(value):
	"""Month, Year, and Month Start for any date in that month."""
	month_start = get_first_day(value)
	return {"month": MONTHS[month_start.month - 1], "year": str(month_start.year), "month_start": month_start}


def get_months(start, end):
	"""First day of every month from start to end; empty when either is missing."""
	months = []
	month = get_first_day(start) if start and end else None
	while month and month <= get_first_day(end):
		months.append(month)
		month = add_months(month, 1)
	return months


def get_distribution(task, employee):
	"""Spread the employee's unplanned task budget across the task's months by working time."""
	budget = get_budget(task, employee)
	if not budget:
		frappe.throw(_("No Hours Budget for {0} on this task.").format(employee))
	months = get_months(*frappe.db.get_value("Task", task, ["exp_start_date", "exp_end_date"]))
	if not months:
		frappe.throw(_("Set the task's From and To dates before distributing."))
	planned = frappe.get_all(
		"Task Allocation",
		filters={"task": task, "employee": employee, "docstatus": ("<", 2)},
		fields=["sum(hours) as hours"],
	)
	remaining = budget.hours - flt(planned[0].hours if planned else 0)
	if remaining <= HOURS_TOLERANCE:
		frappe.throw(
			_(
				"Nothing left to distribute: submitted and draft allocations already use the {0}h budget."
			).format(f"{budget.hours:g}")
		)
	weights = [get_available_hours(employee, month) for month in months]
	evenly = None in weights or not sum(weights)
	if evenly:
		weights = [1] * len(months)
	return {
		"remaining": remaining,
		"evenly": evenly,
		"months": [
			{**get_month_fields(month), "month_start": str(month), "hours": hours}
			for month, hours in zip(months, spread_hours(remaining, weights), strict=True)
		],
	}


def spread_hours(total, weights):
	"""Split total by weight in half hours; the last share takes the rounding difference."""
	whole = sum(weights)
	shares = [round(total * weight / whole * 2) / 2 for weight in weights[:-1]]
	return [*shares, max(round(total - sum(shares), 2), 0)]


def create_distribution(task, employee, rows):
	"""Create one draft allocation per month with hours and return their names."""
	names = []
	for row in rows:
		if flt(row.get("hours")) <= 0:
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Task Allocation",
				"task": task,
				"employee": employee,
				"month": row["month"],
				"year": str(row["year"]),
				"hours": flt(row["hours"]),
			}
		)
		names.append(doc.insert().name)
	return names


def get_allocation_grid(task):
	"""Submitted allocation and timesheet hours per employee and month for the Task form grid."""
	allocations = frappe.get_all(
		"Task Allocation",
		filters={"task": task, "docstatus": 1},
		fields=["employee", "personnel_name as employee_name", "month_start", "sum(hours) as hours"],
		group_by="employee, personnel_name, month_start",
		order_by="personnel_name, month_start",
	)
	used = frappe.db.sql(
		"""
		SELECT ts.employee, ts.employee_name, DATE_FORMAT(tl.from_time, '%%Y-%%m-01') AS month,
			SUM(tl.hours) AS hours
		FROM `tabTimesheet` ts JOIN `tabTimesheet Detail` tl ON tl.parent = ts.name
		WHERE ts.docstatus = 1 AND tl.task = %s AND IFNULL(ts.employee, '') != ''
		GROUP BY ts.employee, ts.employee_name, DATE_FORMAT(tl.from_time, '%%Y-%%m-01')
		""",
		task,
		as_dict=True,
	)
	start, end = frappe.db.get_value("Task", task, ["exp_start_date", "exp_end_date"])
	months = {str(row.month_start) for row in allocations} | {row.month for row in used}
	months |= {str(month) for month in get_months(start, end)}
	budgets = frappe.db.sql(
		"""
		SELECT b.personnel AS employee, e.employee_name, b.hours, b.overrun
		FROM `tabTask Time Allocation` b LEFT JOIN `tabEmployee` e ON e.name = b.personnel
		WHERE b.parent = %s AND b.parenttype = 'Task' AND IFNULL(b.personnel, '') != ''
		""",
		task,
		as_dict=True,
	)
	employees = {row.employee: row.employee_name for row in allocations + used + budgets}
	return {
		"budgets": {
			row.employee: {
				"hours": flt(row.hours),
				"overrun": flt(row.overrun),
			}
			for row in budgets
		},
		"months": sorted(months),
		"employees": [
			{"employee": employee, "employee_name": name or employee}
			for employee, name in sorted(employees.items(), key=lambda item: (item[1] or item[0]).lower())
		],
		"allocated": [[row.employee, str(row.month_start), flt(row.hours)] for row in allocations],
		"used": [[row.employee, row.month, flt(row.hours)] for row in used],
		"can_create": bool(frappe.has_permission("Task Allocation", "create")),
	}
