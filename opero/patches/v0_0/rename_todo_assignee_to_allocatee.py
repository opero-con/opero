from __future__ import annotations

"""Rename ToDo Assignee child-doctype → ToDo Allocatee and
custom_assignees field → custom_allocatees to align with Frappe's
'allocated_to' naming convention.

The pre_model_sync companion patch (restore_todo_allocatee_custom_field) seeds
the Custom Field before model sync so the orphan-cleanup pass won't delete the
newly synced "ToDo Allocatee" DocType.  This post_model_sync patch handles the
remaining data-migration work and ensures the Custom Field is correct (it may
have been cascade-deleted if orphan cleanup ran before the class name was
fixed).
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    # 1. Rename the child DocType if it still goes by the old name.
    if frappe.db.exists("DocType", "ToDo Assignee") and not frappe.db.exists(
        "DocType", "ToDo Allocatee"
    ):
        frappe.rename_doc("DocType", "ToDo Assignee", "ToDo Allocatee", force=True)

    # 2. Ensure the Custom Field exists with the correct attributes.
    #    Use create_custom_fields so it is idempotent (insert or update).
    if frappe.db.exists("DocType", "ToDo Allocatee"):
        create_custom_fields(
            {
                "ToDo": [
                    {
                        "fieldname": "custom_allocatees",
                        "label": "Allocatees",
                        "fieldtype": "Table MultiSelect",
                        "options": "ToDo Allocatee",
                        "insert_after": "custom_title",
                        "description": "Select one or more users to allocate this task to.",
                    },
                ]
            },
            ignore_validate=True,
            update=True,
        )

    # 3. Clean up any stale record still pointing to the old DocType.
    frappe.db.sql(
        "UPDATE `tabCustom Field` SET options = 'ToDo Allocatee' WHERE options = 'ToDo Assignee'"
    )

    # 4. Rename the Custom Field fieldname custom_assignees → custom_allocatees
    cf = frappe.db.exists(
        "Custom Field", {"dt": "ToDo", "fieldname": "custom_assignees"}
    )
    if cf:
        frappe.db.set_value(
            "Custom Field", cf, "fieldname", "custom_allocatees", update_modified=False
        )
        # Rename the DB column only if the old name still exists.
        if "custom_assignees" in frappe.db.get_table_columns("ToDo"):
            frappe.db.sql_ddl(
                "ALTER TABLE `tabToDo` RENAME COLUMN `custom_assignees` TO `custom_allocatees`"
            )

    # 5. Migrate child rows from the old table into the new one.
    if frappe.db.table_exists("ToDo Assignee") and frappe.db.table_exists("ToDo Allocatee"):
        pending = frappe.db.sql(
            "SELECT 1 FROM `tabToDo Assignee` WHERE parentfield = 'custom_assignees' LIMIT 1"
        )
        if pending:
            frappe.db.sql(
                """INSERT IGNORE INTO `tabToDo Allocatee`
                   SELECT * FROM `tabToDo Assignee`
                   WHERE parentfield = 'custom_assignees'"""
            )
            frappe.db.sql(
                "UPDATE `tabToDo Allocatee` SET parentfield = 'custom_allocatees' WHERE parentfield = 'custom_assignees'"
            )
            frappe.db.sql(
                "DELETE FROM `tabToDo Assignee` WHERE parentfield = 'custom_assignees'"
            )

    # 6. Update parentfield in any remaining allocatee rows.
    if frappe.db.table_exists("ToDo Allocatee"):
        frappe.db.sql(
            "UPDATE `tabToDo Allocatee` SET parentfield = 'custom_allocatees' WHERE parentfield = 'custom_assignees'"
        )

    # 7. Update any Property Setters referencing the old field name.
    frappe.db.sql(
        "UPDATE `tabProperty Setter` SET field_name = 'custom_allocatees' WHERE doc_type = 'ToDo' AND field_name = 'custom_assignees'"
    )

    frappe.clear_cache(doctype="ToDo")
    if frappe.db.exists("DocType", "ToDo Allocatee"):
        frappe.clear_cache(doctype="ToDo Allocatee")
