from opero.patches.v0_0.fix_todo_top_section_field_order import execute as fix_todo_top_section_field_order


def execute():
	# Re-apply top section ordering to keep ToDo description_and_status
	# in the standard two-column flow.
	fix_todo_top_section_field_order()
