"""Show the Task's Hours Budget again and record each person's committed hours and overrun.

Duplicate rows for one person are merged. Budgets are not changed: where submitted
allocations exceed a budget, or a person has allocations but no row, the excess is
stored as the row's Overrun (on a zero-budget row when none existed).
"""

import json
from pathlib import Path

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import flt

from opero.opero.doctype.task_allocation.task_allocation import (
	HOURS_TOLERANCE,
	get_budget,
	get_overrun,
	update_budget_usage,
)

CUSTOM_FIELDS_FILE = Path(__file__).parents[1] / "v0_2" / "standard_doctype_custom_fields.json"


def execute():
	show_hours_budget()
	merge_duplicate_budget_rows()
	pairs = frappe.get_all(
		"Task Allocation",
		filters={"docstatus": 1},
		fields=["task", "employee", "sum(hours) as hours"],
		group_by="task, employee",
	)
	for pair in pairs:
		update_budget_usage(pair.task, pair.employee)

	wrong = [pair for pair in pairs if not has_expected_usage(pair)]
	if wrong:
		frappe.throw(
			f"Hours Budget committed hours or overrun do not match allocations for {len(wrong)} task/person pairs."
		)


def has_expected_usage(pair):
	budget = get_budget(pair.task, pair.employee)
	expected = get_overrun(pair.hours, budget.hours if budget else 0)
	if not budget:
		return not expected
	return (
		abs(budget.overrun - expected) <= HOURS_TOLERANCE
		and abs(flt(budget.committed) - flt(pair.hours)) <= HOURS_TOLERANCE
	)


def show_hours_budget():
	row = next(
		row
		for row in json.loads(CUSTOM_FIELDS_FILE.read_text())
		if row["name"] == "Task-custom_time_allocation"
	)
	keep = ("fieldname", "label", "fieldtype", "insert_after", "options", "hidden")
	create_custom_fields({"Task": [{key: row.get(key) for key in keep}]}, update=True)
	frappe.clear_cache(doctype="Task")


def merge_duplicate_budget_rows():
	duplicates = frappe.db.sql(
		"""
		SELECT parent, personnel, SUM(hours) AS hours
		FROM `tabTask Time Allocation`
		WHERE parenttype = 'Task' AND personnel IS NOT NULL
		GROUP BY parent, personnel
		HAVING COUNT(*) > 1
		""",
		as_dict=True,
	)
	for row in duplicates:
		rows = frappe.get_all(
			"Task Time Allocation",
			filters={"parent": row.parent, "parenttype": "Task", "personnel": row.personnel},
			pluck="name",
			order_by="idx",
		)
		frappe.db.set_value("Task Time Allocation", rows[0], "hours", flt(row.hours))
		frappe.db.delete("Task Time Allocation", {"name": ["in", rows[1:]]})
