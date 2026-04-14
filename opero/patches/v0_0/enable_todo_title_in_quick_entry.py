from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"ToDo": [
				{
					"fieldname": "custom_title",
					"allow_in_quick_entry": 1,
				}
			]
		},
		update=True,
	)
