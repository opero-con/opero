from __future__ import annotations

"""Rename ToDo Allocatee child-doctype → ToDo Assignee and
custom_allocatees field → custom_assignees.

The pre_model_sync companion patch (restore_todo_assignee_custom_field) seeds
the Custom Field before model sync so Frappe's orphan-cleanup pass won't delete
the newly synced "ToDo Assignee" DocType.  This post_model_sync patch handles
the remaining data-migration work.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    # 1. Rename the child DocType if still under the old name.
    if frappe.db.exists("DocType", "ToDo Allocatee") and not frappe.db.exists(
        "DocType", "ToDo Assignee"
    ):
        frappe.rename_doc("DocType", "ToDo Allocatee", "ToDo Assignee", force=True)

    # 2. Ensure the Custom Field exists with correct attributes.
    if frappe.db.exists("DocType", "ToDo Assignee"):
        create_custom_fields(
            {
                "ToDo": [
                    {
                        "fieldname": "custom_assignees",
                        "label": "Assignees",
                        "fieldtype": "Table MultiSelect",
                        "options": "ToDo Assignee",
                        "insert_after": "custom_title",
                        "description": "Select one or more users to assign this task to.",
                    }
                ]
            },
            ignore_validate=True,
            update=True,
        )

    # 3. Clean up any stale Custom Field still pointing to the old DocType.
    frappe.db.sql(
        "UPDATE `tabCustom Field` SET options = 'ToDo Assignee' WHERE options = 'ToDo Allocatee'"
    )

    # 4. Rename the Custom Field fieldname custom_allocatees → custom_assignees.
    cf = frappe.db.exists("Custom Field", {"dt": "ToDo", "fieldname": "custom_allocatees"})
    if cf:
        frappe.db.set_value(
            "Custom Field", cf, "fieldname", "custom_assignees", update_modified=False
        )
        if "custom_allocatees" in frappe.db.get_table_columns("ToDo"):
            frappe.db.sql_ddl(
                "ALTER TABLE `tabToDo` RENAME COLUMN `custom_allocatees` TO `custom_assignees`"
            )

    # 5. Migrate child rows from old table into new one.
    if frappe.db.table_exists("ToDo Allocatee") and frappe.db.table_exists("ToDo Assignee"):
        pending = frappe.db.sql(
            "SELECT 1 FROM `tabToDo Allocatee` WHERE parentfield = 'custom_allocatees' LIMIT 1"
        )
        if pending:
            frappe.db.sql(
                """INSERT IGNORE INTO `tabToDo Assignee`
                   SELECT * FROM `tabToDo Allocatee`
                   WHERE parentfield = 'custom_allocatees'"""
            )
            frappe.db.sql(
                "DELETE FROM `tabToDo Allocatee` WHERE parentfield = 'custom_allocatees'"
            )

    # 6. Update parentfield in any remaining rows.
    if frappe.db.table_exists("ToDo Assignee"):
        frappe.db.sql(
            "UPDATE `tabToDo Assignee` SET parentfield = 'custom_assignees' WHERE parentfield = 'custom_allocatees'"
        )

    # 7. Update Property Setters.
    frappe.db.sql(
        "UPDATE `tabProperty Setter` SET field_name = 'custom_assignees' WHERE doc_type = 'ToDo' AND field_name = 'custom_allocatees'"
    )

    frappe.clear_cache(doctype="ToDo")
    if frappe.db.exists("DocType", "ToDo Assignee"):
        frappe.clear_cache(doctype="ToDo Assignee")
