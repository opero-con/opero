"""Allow a native mailing member to be added by selecting a Contact."""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Email Group Member": [
				{
					"fieldname": "custom_contact",
					"label": "Contact",
					"fieldtype": "Link",
					"options": "Contact",
					"insert_after": "email_group",
					"in_standard_filter": 1,
					"in_list_view": 1,
					"allow_in_quick_entry": 1,
					"module": "Opero",
					"description": "Select an existing Contact to use their primary email, or leave blank to enter an email address.",
				},
			]
		},
		update=True,
	)
