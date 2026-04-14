from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"ToDo": [
				{
					"fieldname": "custom_title",
					"insert_after": "description_and_status",
				}
			]
		},
		update=True,
	)
