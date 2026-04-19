# Opero

A Frappe v15 app that enhances the ToDo doctype with multi-assignee support, lifecycle tracking, a Flow Hub kanban-style page, and reporting.

---

## Features

### ToDo Enhancements

Opero extends the standard Frappe ToDo with fields and behaviour that make it usable as a lightweight task management system.

**Fields added to ToDo:**

| Field | Purpose |
|---|---|
| `custom_title` | Plain-text title shown as the primary identifier. Falls back to `description` if left blank. |
| `custom_assignees` | Table MultiSelect of one or more users (child doctype: `ToDo Assignee`). The first entry is always mirrored to Frappe's native `allocated_to` field. |
| `custom_created_by` | Display name of the user who created the ToDo, synced from `owner`. |
| `custom_closed_on` | Timestamp set automatically when status moves to Closed. Cleared if status changes away. |
| `custom_cancelled_on` | Timestamp set automatically when status moves to Cancelled. Cleared if status changes away. |
| `custom_parent_todo` | Link to the parent ToDo for group-child records (internal use). |
| `custom_is_group_child` | Flag marking a ToDo as a child created by group assignment (internal use). |
| `custom_assignment_group` | Shared identifier linking a parent ToDo and all its group children. |

**Status values:**

`Open` · `In Progress` · `Closed` · `Cancelled`

**Behaviour:**

- Saving a ToDo with multiple assignees creates child ToDos (one per secondary assignee) that stay in sync with the parent's title, description, priority, due date, and reference.
- Removing an assignee deletes the corresponding child ToDo.
- Changing the primary assignee updates `allocated_to` and creates a Frappe Notification Log for the new assignee.
- New assignees also receive a Notification Log on insert.

---

### Assignees Sidebar

On the ToDo form, the native **Assigned To** sidebar section is replaced by an **Assignees** section that reads from and writes to `custom_assignees`.

- Shows user avatars using Frappe's standard avatar group component.
- Clicking the avatars or the **+** button opens a dialog to add or remove assignees.
- Changes save immediately and re-render the sidebar in place.

---

### Flow Hub

A custom page (`/app/flow-hub`) that presents open and in-progress ToDos in a card layout grouped by status. Supports quick assignee management directly from the card without opening the full form.

---

### Reports

| Report | Description |
|---|---|
| ToDo Action Queue | Prioritised list of open and in-progress ToDos. Default sort: overdue first, then due today, then priority. |
| ToDo Explorer | Full filterable view of all ToDos with assignee breakdown. |
| ToDo Created vs Closed | Line chart comparing creation and closure rates over a date range. |
| ToDo In Progress Aging | Shows how long ToDos have been sitting in In Progress status. |
| ToDo Assignee Load and Risk | Per-user workload summary with overdue and at-risk counts. |

---

### ToDo Hub Workspace

A pre-built workspace with number cards (My Overdue, Due Today, In Progress, Unassigned) and shortcuts to the reports and Flow Hub.

---

## Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO
bench install-app opero
bench migrate
```

---

## Requirements

- Frappe v15
- Python 3.10+

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

---

## License

MIT
