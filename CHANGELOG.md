# Changelog

## 0.2.0 — 2026-04-19

### Breaking changes

- Renamed child doctype `ToDo Allocatee` to `ToDo Assignee`.
- Renamed custom field `custom_allocatees` to `custom_assignees` on the ToDo doctype. The database column and all child table rows are migrated automatically by the included patches.
- Any external code, reports, or scripts that reference `custom_allocatees` or `tabToDo Allocatee` must be updated to use `custom_assignees` and `tabToDo Assignee`.

### Features

- **Assignees sidebar**: The ToDo form now shows an Assignees section in the sidebar using Frappe's avatar group component. Users can add and remove assignees directly from the sidebar without opening the field on the form. The native Assigned To section is hidden to avoid duplication.
- **Assignment notifications**: Creating a ToDo or changing its assignees now creates a Frappe Notification Log for each affected user, enabling downstream notification apps (such as reyal_telegram) to route alerts.

### Internal

- Terminology aligned throughout: field names, Python functions, SQL queries, and UI labels all use "assignee/assignees" consistently.
- Two migration patches added (`restore_todo_assignee_custom_field` pre-model-sync, `rename_todo_allocatee_to_assignee` post-model-sync) to handle the rename on existing sites.

---

## 0.1.0 — 2026-04-14

Initial release.

- ToDo enhancements: `custom_title`, `custom_assignees` (multi-assignee via Table MultiSelect), `custom_created_by`, `custom_closed_on`, `custom_cancelled_on`, group assignment with parent/child ToDo sync.
- Flow Hub custom page.
- Reports: ToDo Action Queue, ToDo Explorer, ToDo Created vs Closed, ToDo In Progress Aging, ToDo Assignee Load and Risk.
- ToDo Hub workspace with number cards and shortcuts.
