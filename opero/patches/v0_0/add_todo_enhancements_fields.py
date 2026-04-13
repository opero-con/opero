from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"ToDo": [
				{
					"fieldname": "custom_title",
					"label": "Title",
					"fieldtype": "Data",
					"insert_after": "description",
					"in_list_view": 1,
				},
				{
					"fieldname": "custom_additional_assignees",
					"label": "Additional Assignees",
					"fieldtype": "Small Text",
					"insert_after": "allocated_to",
					"description": "Add one user ID per line (for example: user@example.com).",
				},
				{
					"fieldname": "custom_parent_todo",
					"label": "Parent ToDo",
					"fieldtype": "Link",
					"options": "ToDo",
					"insert_after": "custom_additional_assignees",
					"hidden": 1,
					"read_only": 1,
					"no_copy": 1,
				},
				{
					"fieldname": "custom_assignment_group",
					"label": "Assignment Group",
					"fieldtype": "Data",
					"insert_after": "custom_parent_todo",
					"hidden": 1,
					"read_only": 1,
					"no_copy": 1,
				},
				{
					"fieldname": "custom_is_group_child",
					"label": "Is Group Child",
					"fieldtype": "Check",
					"default": "0",
					"insert_after": "custom_assignment_group",
					"hidden": 1,
					"read_only": 1,
					"no_copy": 1,
				},
			]
		},
		update=True,
	)
