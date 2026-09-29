"""Copy Task Time Distribution months into submitted Task Allocations and switch the Task form to the grid.

Monthly rows win over the task's per-person totals. A per-person total with no
monthly hours lands in the task's end month. Months that cannot be read take the
task's start month (or its start year for a bare month name); a task with no
dates falls back to its project's start.
"""

import json
from datetime import datetime
from pathlib import Path

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import flt, get_first_day

from opero import entity
from opero.opero.doctype.task_allocation.task_allocation import get_month_fields
from opero.patches.v0_2.import_fc_site_config import DATA_DIR, _upsert

TASK_FIELDS = ["custom_time_allocation", "custom_total_days", "custom_allocation_grid"]
CUSTOM_FIELDS_FILE = Path(__file__).parents[1] / "v0_2" / "standard_doctype_custom_fields.json"


def execute():
	update_task_form()
	link_task_to_allocations()
	frappe.reload_doc("opero", "workspace", "opero", force=True)
	if frappe.db.count("Task Allocation"):
		frappe.throw("Task Allocation already has records; refusing to copy Task Time Distribution twice.")

	allocations = build_allocations(get_spread_rows(), get_task_totals(), get_task_dates())
	insert_allocations(allocations)
	recompute_totals()

	expected = round(sum(row["hours"] for row in allocations.values()), 4)
	copied = round(
		flt(frappe.db.sql("SELECT SUM(hours) FROM `tabTask Allocation` WHERE docstatus = 1")[0][0]), 4
	)
	if expected != copied:
		frappe.throw(f"Task Allocation copy mismatch: expected {expected}h, copied {copied}h.")


def update_task_form():
	fields = [row for row in json.loads(CUSTOM_FIELDS_FILE.read_text()) if row["dt"] == "Task"]
	keep = ("fieldname", "label", "fieldtype", "insert_after", "options", "read_only", "hidden")
	create_custom_fields(
		{"Task": [{key: row.get(key) for key in keep} for row in fields if row["fieldname"] in TASK_FIELDS]},
		update=True,
	)
	setters = {doc["name"]: doc for doc in json.loads((DATA_DIR / "property_setter.json").read_text())}
	_upsert(setters["Task-main-field_order"])
	frappe.clear_cache(doctype="Task")


def link_task_to_allocations():
	"""Point the Task's Connections entry at Task Allocation instead of Task Time Distribution."""
	values = {"link_doctype": "Task Allocation", "link_fieldname": "task"}
	legacy = frappe.db.get_value("DocType Link", {"parent": "Task", "link_doctype": "Task Time Distribution"})
	if legacy:
		frappe.db.set_value("DocType Link", legacy, values)
	elif not frappe.db.exists("DocType Link", {"parent": "Task", "link_doctype": "Task Allocation"}):
		frappe.get_doc(
			{
				"doctype": "DocType Link",
				"parent": "Task",
				"parenttype": "Customize Form",
				"parentfield": "links",
				"group": "Links",
				"custom": 1,
				**values,
			}
		).db_insert()
	frappe.clear_cache(doctype="Task")


def get_task_dates():
	rows = frappe.db.sql(
		"""
		SELECT t.name, t.exp_start_date, t.exp_end_date, p.expected_start_date AS project_start_date
		FROM `tabTask` t LEFT JOIN `tabProject` p ON p.name = t.project
		""",
		as_dict=True,
	)
	return {row.name: row for row in rows}


def get_spread_rows():
	return frappe.db.sql(
		"""
		SELECT ttd.project_task AS task, ttd.personnel AS employee, ttds.month,
			ttds.time_spread AS hours, ttds.deliverables, ttds.name AS row_name
		FROM `tabTask Time Distribution` ttd
		JOIN `tabTask Time Distribution Spread` ttds ON ttds.parent = ttd.name
		ORDER BY ttd.name, ttds.idx
		""",
		as_dict=True,
	)


def get_task_totals():
	return frappe.db.sql(
		"""
		SELECT parent AS task, personnel AS employee, SUM(hours) AS hours
		FROM `tabTask Time Allocation`
		WHERE parenttype = 'Task' AND personnel IS NOT NULL
		GROUP BY parent, personnel
		""",
		as_dict=True,
	)


def build_allocations(spread_rows, task_totals, tasks):
	"""Map (task, employee, month) to hours and deliverables."""
	allocations = {}
	spread_pairs = set()
	for row in spread_rows:
		hours = flt(row.hours)
		deliverables = (row.deliverables or "").strip()
		if hours <= 0 and not deliverables:
			continue
		spread_pairs.add((row.task, row.employee))
		task = tasks.get(row.task)
		if not task:
			frappe.throw(f"Task Time Distribution Spread {row.row_name} points at missing task {row.task}.")
		add_allocation(
			allocations,
			row.task,
			row.employee,
			parse_month(row.month, task, row.row_name),
			hours,
			deliverables,
		)

	for row in task_totals:
		if flt(row.hours) <= 0 or (row.task, row.employee) in spread_pairs:
			continue
		task = tasks.get(row.task)
		month = task and (task.exp_end_date or task.exp_start_date or task.project_start_date)
		if not month:
			frappe.throw(f"Task {row.task} has allocated hours but no dates to place them in.")
		add_allocation(allocations, row.task, row.employee, get_first_day(month), flt(row.hours), "")
	return allocations


def add_allocation(allocations, task, employee, month, hours, deliverables):
	entry = allocations.setdefault((task, employee, month), {"hours": 0, "deliverables": []})
	entry["hours"] += hours
	if deliverables:
		entry["deliverables"].append(deliverables)


def parse_month(text, task, row_name):
	text = (text or "").strip().replace("Sept ", "Sep ")
	start = task.exp_start_date or task.exp_end_date or task.project_start_date
	for pattern in ("%b %Y", "%B %Y"):
		try:
			return datetime.strptime(text, pattern).date()
		except ValueError:
			pass
	if not start:
		frappe.throw(
			f"Task Time Distribution Spread {row_name} has month {text!r} and its task has no dates."
		)
	if not text:
		return get_first_day(start)
	try:
		return datetime.strptime(f"{text} {start.year}", "%B %Y").date()
	except ValueError:
		frappe.throw(f"Task Time Distribution Spread {row_name} has an unreadable month {text!r}.")


def insert_allocations(allocations):
	projects = dict(frappe.get_all("Task", fields=["name", "project"], as_list=True))
	names = dict(frappe.get_all("Employee", fields=["name", "employee_name"], as_list=True))
	for (task, employee, month), entry in allocations.items():
		doc = frappe.get_doc(
			{
				"doctype": "Task Allocation",
				"docstatus": 1,
				"task": task,
				"project": projects.get(task),
				"company": entity.get_project_company(projects.get(task)),
				"employee": employee,
				"personnel_name": names.get(employee),
				"hours": entry["hours"],
				"deliverables": "\n".join(entry["deliverables"]) or None,
				**get_month_fields(month),
			}
		)
		doc.flags.update(ignore_validate=True, ignore_links=True, ignore_permissions=True, skip_totals=True)
		doc.insert()


def recompute_totals():
	frappe.db.sql(
		"""
		UPDATE `tabTask` t
		SET t.custom_total_hours = (SELECT COALESCE(SUM(a.hours), 0) FROM `tabTask Allocation` a WHERE a.docstatus = 1 AND a.task = t.name)
		"""
	)
	frappe.db.sql(
		"""
		UPDATE `tabProject` p
		SET p.custom_allocated_hours = (
			SELECT COALESCE(SUM(a.hours), 0) FROM `tabTask Allocation` a WHERE a.docstatus = 1 AND a.project = p.name
		)
		"""
	)
