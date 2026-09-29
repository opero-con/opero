"""Task Allocation form ribbon and Task grid."""

import frappe

from opero.opero.doctype.task_allocation import task_allocation


@frappe.whitelist()
def get_allocation_grid(task):
	frappe.get_doc("Task", task).check_permission("read")
	return task_allocation.get_allocation_grid(task)


@frappe.whitelist()
def get_capacity(employee, month, year, task=None, name=None):
	frappe.has_permission("Task Allocation", "read", throw=True)
	month_start = task_allocation.get_month_start(month, year)
	result = {**task_allocation.get_capacity(employee, month_start, exclude=name), "same_task": []}
	if task:
		exclude = {"name": ("!=", name)} if name else {}
		result.update(
			same_task=task_allocation.get_same_task_allocations(task, employee, month_start, exclude=name),
			budget=task_allocation.get_budget(task, employee),
			task_subject=frappe.db.get_value("Task", task, "subject"),
			task_allocated=task_allocation.get_allocated_hours(task=task, employee=employee, **exclude),
		)
	return result


@frappe.whitelist()
def get_distribution(task, employee):
	frappe.get_doc("Task", task).check_permission("read")
	return task_allocation.get_distribution(task, employee)


@frappe.whitelist(methods=["POST"])
def create_distribution(task, employee, rows):
	frappe.get_doc("Task", task).check_permission("read")
	return task_allocation.create_distribution(task, employee, frappe.parse_json(rows))
