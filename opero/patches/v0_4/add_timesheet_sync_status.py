"""Expose background timesheet sync status and actionable failures."""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Timesheet": [
				{
					"fieldname": "custom_zoho_sync_status",
					"label": "Zoho Sync Status",
					"fieldtype": "Select",
					"options": "\nPending\nSynced\nPartial\nFailed\nCancelled",
					"read_only": 1,
					"allow_on_submit": 1,
					"insert_after": "note",
				},
				{
					"fieldname": "custom_zoho_sync_error",
					"label": "Zoho Sync Error",
					"fieldtype": "Small Text",
					"read_only": 1,
					"allow_on_submit": 1,
					"insert_after": "custom_zoho_sync_status",
					"depends_on": "eval:doc.custom_zoho_sync_error",
				},
			],
			"Timesheet Detail": [
				{
					"fieldname": "custom_zoho_sync_uncertain",
					"label": "Zoho entry needs review",
					"fieldtype": "Check",
					"read_only": 1,
					"allow_on_submit": 1,
					"insert_after": "description",
					"default": "0",
				},
			],
		}
	)
