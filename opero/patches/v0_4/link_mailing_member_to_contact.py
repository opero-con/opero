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
				},
				{
					"fieldname": "custom_mobile_no",
					"label": "Mobile No",
					"fieldtype": "Data",
					"options": "Phone",
					"insert_after": "custom_contact",
					"fetch_from": "custom_contact.mobile_no",
					"read_only": 1,
					"depends_on": "eval:doc.custom_contact",
					"in_list_view": 1,
					"module": "Opero",
				},
			]
		},
		update=True,
	)
