from opero.patches.v0_0.add_todo_enhancements_fields import execute as add_todo_enhancements_fields
from opero.patches.v0_0.add_todo_in_progress_status import execute as add_todo_in_progress_status
from opero.patches.v0_0.add_todo_owner_display_field import execute as add_todo_owner_display_field
from opero.patches.v0_0.apply_todo_three_column_meta_layout import execute as apply_todo_three_column_meta_layout
from opero.patches.v0_0.backfill_todo_assignee_rows import execute as backfill_todo_assignee_rows
from opero.patches.v0_0.convert_todo_assignees_to_table_multiselect import (
	execute as convert_todo_assignees_to_table_multiselect,
)
from opero.patches.v0_0.enable_todo_title_in_quick_entry import execute as enable_todo_title_in_quick_entry
from opero.patches.v0_0.hide_todo_color_field import execute as hide_todo_color_field
from opero.patches.v0_0.hide_todo_role_field import execute as hide_todo_role_field
from opero.patches.v0_0.make_todo_description_optional import execute as make_todo_description_optional
from opero.patches.v0_0.rename_todo_owner_field_to_created_by import execute as rename_todo_owner_field_to_created_by
from opero.patches.v0_0.reposition_todo_title_before_status import execute as reposition_todo_title_before_status
from opero.patches.v0_0.set_todo_title_field_to_custom_title import execute as set_todo_title_field_to_custom_title


def execute():
	# Re-apply all ToDo enhancements as a single fresh patch for sites where older
	# patches were already marked executed before we adjusted their implementation.
	add_todo_enhancements_fields()
	reposition_todo_title_before_status()
	apply_todo_three_column_meta_layout()
	make_todo_description_optional()
	enable_todo_title_in_quick_entry()
	add_todo_owner_display_field()
	rename_todo_owner_field_to_created_by()
	hide_todo_color_field()
	hide_todo_role_field()
	add_todo_in_progress_status()
	set_todo_title_field_to_custom_title()
	convert_todo_assignees_to_table_multiselect()
	backfill_todo_assignee_rows()
