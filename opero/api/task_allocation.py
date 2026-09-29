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
	return {
		**task_allocation.get_capacity(employee, month_start, exclude=name),
		"same_task": task_allocation.get_same_task_allocations(task, employee, month_start, exclude=name)
		if task
		else [],
	}
