# Changelog

## 0.2.26 — 2026-05-06

### Changed

- Revamped the Flow Hub detail card into a structured header/body/footer layout with in-panel actions.
- Added direct detail actions for `Mark done`, `Assign`, `Set/Change due`, and `Priority`.
- Refined queue/detail split behavior so the detail panel slides in while the queue shifts for better screen use.
- Standardized Flow Hub typography to Frappe font and text tokens (`--font-stack`, `--text-*`, `--weight-*`).
- Shortened due-date copy to compact day notation (`Xd`) in Flow Hub and ToDo due-date descriptors.

### Fixed

- Prevented the detail panel right border from clipping against page/container scroll edges.

---

## 0.2.25 — 2026-05-05

### Fixed

- Restored reliable relative-time progression in the Flow Hub status bar after the tooltip redesign by reusing Frappe's native `comment_when` timestamp rendering (`now` -> `1 min` -> `2 mins` ...).
- Fixed a regression where "Last updated" could remain stuck at `now` instead of aging automatically.
- Normalized server datetime parsing (`YYYY-MM-DD HH:mm:ss[.ffffff]`) before rendering relative labels to avoid browser parsing inconsistencies.
- Ensured the "Last updated" tooltip uses the user's profile timezone (via Frappe user timezone conversion) rather than raw site/system interpretation.
- Kept the rich two-line tooltip layout ("Last updated" + full timestamp) while restoring native timestamp semantics.

### Changed

- Aligned status-bar recency behavior with core Frappe timestamp mechanics so future Flow Hub changes can depend on consistent relative-time refresh behavior.

---

## 0.2.24 — 2026-05-04

### Fixed

- Kept Flow Hub synchronized with the live ToDo document state by removing the cached snapshot path.
- Added stale-write protection for Flow Hub edits using each ToDo row's `modified` timestamp.
- Routed Flow Hub priority, due date, and assignee changes through server-side ToDo saves so form views and database state stay aligned.
- Subscribed Flow Hub to Frappe realtime ToDo list updates so form-side changes refresh the hub promptly.

### Changed

- Shortened the Flow Hub status-bar timestamp to compact labels such as `1 min ago`.
- Restored the two-line "Last updated" tooltip while using normal text weight for the tooltip label.

---

## 0.2.23 — 2026-05-01

### Fixed

- Polished Flow Hub split detail and queue behaviour.
- Improved Flow Hub UI consistency around status chips, detail state, and queue refreshes.

---

## 0.2.22 — 2026-05-01

### Changed

- Shortened due-date labels in the Flow Hub queue.
- Added rich due-date tooltips so compact labels still expose the full due context.
- Refined the ToDo form Flow Hub navigation button.

---

## 0.2.21 — 2026-04-30

### Changed

- Redesigned the Flow Hub status bar.
- Extended Flow Hub velocity/throughput metrics to a 30-day window.
- Updated the velocity sparkline to match the longer reporting window.

---

## 0.2.20 — 2026-04-30

### Fixed

- Refined Flow Hub tooltip behaviour.
- Improved Flow Hub status chip styling and interaction polish.

---

## 0.2.19 — 2026-04-30

### Fixed

- Replaced child-ToDo fan-out with permission-based multi-assignee visibility.
- Added migration cleanup for older generated child ToDos.
- Prevented duplicate ToDos from appearing as a side effect of multi-assignee workflows.

---

## 0.2.17 — 2026-04-29

### Fixed

- Improved Zoho sync error handling and diagnostics.
- Added clearer sync notifications for success and failure paths.
- Hardened token refresh handling when Zoho returns an error response.

---

## 0.2.16 — 2026-04-29

### Changed

- Overhauled the Zoho mapping user experience.
- Fixed the Zoho tasks API key path used by the mapping workflow.

---

## 0.2.15 — 2026-04-29

### Changed

- Replaced separate Zoho personnel/project mapping tables with a shared Integration Mapping registry.
- Added migration support to preserve existing Zoho mapping data.
- Added inline Map/Unmap controls for personnel and project mapping.
- Documented release tagging in the workflow docs.

---

## 0.2.14 — 2026-04-29

### Added

- Added Zoho Books timesheet sync integration.
- Added Zoho Books settings, personnel mapping, and project mapping support.
- Added fixtures for Zoho custom fields on Project and Timesheet Detail.
- Added per-project task mapping UI.
- Added ERPNext/Cubenet task auto-match and Zoho task auto-create support.
- Added Zoho setup documentation and contributor workflow docs.

### Fixed

- Fixed OAuth token storage and refresh-token checks for Zoho Books settings.
- Surfaced per-entry sync errors and success confirmations.
- Added visible warnings when personnel mapping is missing.
- Fixed custom field fixture import by including required `name` values.
- Refined Flow Hub card padding, selected-card indicators, and split-view clipping.

---

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
