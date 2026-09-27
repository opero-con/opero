"""Project owns its manager; dependent documents copy the manager from it."""

from __future__ import annotations

import frappe

PM_FIELDS = ("custom_project_manager", "custom_pm_name", "custom_pm_email")

# DocType -> (project link field, {document field: Project field})
PM_COPIES = {
	"Timesheet": (
		"parent_project",
		{field: field for field in PM_FIELDS},
	),
	"Travel Request": (
		"custom_project",
		{field: field for field in PM_FIELDS},
	),
	"Cash Advance-Reimbursable Form": (
		"project",
		{"project_manager": "custom_pm_name", "pm_email": "custom_pm_email"},
	),
	"Consultant Task": (
		"project",
		{
			"project_manager": "custom_project_manager",
			"pm_name": "custom_pm_name",
			"pm_email": "custom_pm_email",
		},
	),
}


def get_project_manager(project: str | None) -> frappe._dict:
	"""Read the manager's name and email from the Employee, not the Project's own copies."""
	employee = frappe.db.get_value("Project", project, "custom_project_manager") if project else None
	person = (
		frappe.db.get_value("Employee", employee, ["employee_name", "user_id"], as_dict=True)
		if employee
		else None
	)
	return frappe._dict(
		custom_project_manager=employee,
		custom_pm_name=person.employee_name if person else None,
		custom_pm_email=person.user_id if person else None,
	)


def copy_project_manager(doc, _method=None):
	project_field, fields = PM_COPIES[doc.doctype]
	manager = get_project_manager(doc.get(project_field))
	for target, source in fields.items():
		doc.set(target, manager[source])


def on_update_project(doc, _method=None):
	if doc.has_value_changed("custom_project_manager"):
		sync_project_manager(doc.name)


def sync_project_manager(project: str):
	"""Point the project's open documents at its current manager."""
	manager = get_project_manager(project)
	for doctype, (project_field, fields) in PM_COPIES.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		meta = frappe.get_meta(doctype)
		values = {target: manager[source] for target, source in fields.items() if meta.has_field(target)}
		if values:
			frappe.db.set_value(
				doctype, {project_field: project, "docstatus": 0}, values, update_modified=False
			)
