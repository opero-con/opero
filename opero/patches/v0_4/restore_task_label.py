"""Call Task "Task" again: drop the site's "Project Task" translation and relabel what used it."""

import frappe

FIELD_LABELS = {
	"Project-custom_allocated_hours": "Allocated Hours (Via Task)",
	"Timesheet Detail-custom_project_task": "Task Name",
}
LINK_LABELS = {"Project Task": "Task", "Project Task List": "Task List"}


def execute():
	frappe.db.delete(
		"Translation", {"language": "en", "source_text": "Task", "translated_text": "Project Task"}
	)

	for name, label in FIELD_LABELS.items():
		if frappe.db.exists("Custom Field", name):
			frappe.db.set_value("Custom Field", name, "label", label)
			frappe.clear_cache(doctype=frappe.db.get_value("Custom Field", name, "dt"))

	public = frappe.get_all("Workspace", filters={"public": 1}, pluck="name")
	for old, new in LINK_LABELS.items():
		frappe.db.set_value(
			"Workspace Link",
			{"parenttype": "Workspace", "parent": ("in", public), "link_to": "Task", "label": old},
			"label",
			new,
		)
	frappe.clear_cache()
