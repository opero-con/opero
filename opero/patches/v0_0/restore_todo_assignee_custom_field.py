from __future__ import annotations

"""Seed the Custom Field custom_assignees → ToDo Assignee before model sync.

Must run in [pre_model_sync] so that Frappe's orphan-DocType cleanup finds a
live Custom Field referencing "ToDo Assignee" and does not delete it.
"""

import frappe


CF_NAME = "ToDo-custom_assignees"
FIELD_DEF = {
    "name": CF_NAME,
    "doctype": "Custom Field",
    "dt": "ToDo",
    "module": "Opero",
    "fieldname": "custom_assignees",
    "label": "Assignees",
    "fieldtype": "Table MultiSelect",
    "options": "ToDo Assignee",
    "insert_after": "custom_title",
    "description": "Select one or more users to assign this task to.",
}


def execute():
    existing = frappe.db.get_value(
        "Custom Field",
        {"dt": "ToDo", "fieldname": "custom_assignees"},
        ["name", "options"],
        as_dict=True,
    )
    if existing and existing.options == "ToDo Assignee":
        return

    old_cf = frappe.db.exists("Custom Field", {"dt": "ToDo", "fieldname": "custom_allocatees"})
    if old_cf:
        frappe.db.set_value(
            "Custom Field",
            old_cf,
            {
                "fieldname": "custom_assignees",
                "label": "Assignees",
                "options": "ToDo Assignee",
                "description": "Select one or more users to assign this task to.",
            },
            update_modified=False,
        )
        if old_cf != CF_NAME:
            frappe.db.sql(
                "UPDATE `tabCustom Field` SET name = %s WHERE name = %s",
                (CF_NAME, old_cf),
            )
        frappe.clear_cache(doctype="ToDo")
        return

    if existing:
        frappe.db.set_value(
            "Custom Field",
            existing.name,
            {"options": "ToDo Assignee"},
            update_modified=False,
        )
        frappe.clear_cache(doctype="ToDo")
        return

    now = frappe.utils.now()
    frappe.db.sql(
        """INSERT INTO `tabCustom Field`
           (name, creation, modified, modified_by, owner, docstatus, idx,
            dt, module, fieldname, label, fieldtype, options, insert_after,
            description)
        VALUES (%s, %s, %s, 'Administrator', 'Administrator', 0, 0,
                'ToDo', 'Opero', 'custom_assignees', 'Assignees',
                'Table MultiSelect', 'ToDo Assignee', 'custom_title',
                'Select one or more users to assign this task to.')""",
        (CF_NAME, now, now),
    )

    frappe.clear_cache(doctype="ToDo")
