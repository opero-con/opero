from __future__ import annotations

"""Add zoho_entry_id custom field to Timesheet Detail to track Zoho Books entries."""

import frappe


def execute():
    existing = frappe.db.get_value(
        "Custom Field",
        {"dt": "Timesheet Detail", "fieldname": "zoho_entry_id"},
        "name",
    )
    if existing:
        return

    now = frappe.utils.now()
    frappe.db.sql(
        """INSERT INTO `tabCustom Field`
           (name, creation, modified, modified_by, owner, docstatus, idx,
            dt, module, fieldname, label, fieldtype, hidden, no_copy, read_only)
        VALUES (%s, %s, %s, 'Administrator', 'Administrator', 0, 0,
                'Timesheet Detail', 'Opero', 'zoho_entry_id', 'Zoho Entry ID',
                'Data', 1, 1, 1)""",
        ("Timesheet Detail-zoho_entry_id", now, now),
    )

    frappe.clear_cache(doctype="Timesheet Detail")
