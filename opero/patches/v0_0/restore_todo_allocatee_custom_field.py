from __future__ import annotations

"""Ensure the Custom Field custom_allocatees → ToDo Allocatee exists before
model sync runs.  This patch must live in [pre_model_sync] so that when Frappe
runs orphan-DocType cleanup (which happens right after model sync), it finds a
Custom Field referencing "ToDo Allocatee" and does not delete it.

Background: the rename patch (rename_todo_assignee_to_allocatee) runs in
[post_model_sync] – too late to prevent the orphan deletion.  Creating the
Custom Field here, before the sync, gives the newly-synced "ToDo Allocatee"
DocType a live reference it needs to survive the cleanup pass.
"""

import frappe


CF_NAME = "ToDo-custom_allocatees"
FIELD_DEF = {
    "name": CF_NAME,
    "doctype": "Custom Field",
    "dt": "ToDo",
    "module": "Opero",
    "fieldname": "custom_allocatees",
    "label": "Allocatees",
    "fieldtype": "Table MultiSelect",
    "options": "ToDo Allocatee",
    "insert_after": "custom_title",
    "description": "Select one or more users to allocate this task to.",
}


def execute():
    # If the field already exists with the right options, nothing to do.
    existing = frappe.db.get_value(
        "Custom Field",
        {"dt": "ToDo", "fieldname": "custom_allocatees"},
        ["name", "options"],
        as_dict=True,
    )
    if existing and existing.options == "ToDo Allocatee":
        return

    # If an old record with the old fieldname/options exists, update it.
    old_cf = frappe.db.exists(
        "Custom Field", {"dt": "ToDo", "fieldname": "custom_assignees"}
    )
    if old_cf:
        frappe.db.set_value(
            "Custom Field",
            old_cf,
            {
                "fieldname": "custom_allocatees",
                "label": "Allocatees",
                "options": "ToDo Allocatee",
                "description": "Select one or more users to allocate this task to.",
            },
            update_modified=False,
        )
        # Rename the record itself to match the convention {dt}-{fieldname}
        if old_cf != CF_NAME:
            frappe.db.sql(
                "UPDATE `tabCustom Field` SET name = %s WHERE name = %s",
                (CF_NAME, old_cf),
            )
        return

    if existing:
        # Wrong options – fix in-place.
        frappe.db.set_value(
            "Custom Field",
            existing.name,
            {"options": "ToDo Allocatee"},
            update_modified=False,
        )
        return

    # No record at all – insert one directly (skip ORM validation because
    # "ToDo Allocatee" DocType may not yet exist in tabDocType at this point).
    now = frappe.utils.now()
    frappe.db.sql(
        """INSERT INTO `tabCustom Field`
           (name, creation, modified, modified_by, owner, docstatus, idx,
            dt, module, fieldname, label, fieldtype, options, insert_after,
            description)
        VALUES (%s, %s, %s, 'Administrator', 'Administrator', 0, 0,
                'ToDo', 'Opero', 'custom_allocatees', 'Allocatees',
                'Table MultiSelect', 'ToDo Allocatee', 'custom_title',
                'Select one or more users to allocate this task to.')""",
        (CF_NAME, now, now),
    )

    frappe.clear_cache(doctype="ToDo")
