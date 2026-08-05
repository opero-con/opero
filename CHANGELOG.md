# Changelog

## 0.2.36 — 2026-08-05

### Changed

- Renamed WaSH DocTypes and labels to all-caps WASH (Water And Sanitation Hygiene): Category, Competency Category, Expert Profile, Expertise Area, and Personnel

---

## 0.2.35 — 2026-08-05

### Added

- Ported enabled Form Client Scripts for Timesheet, Task, Project, Travel Request, and Material Request into `public/js/custom/`
- Server Script fixtures for Timesheet/Task/Travel/ToDo/Comment/HR Settings behaviour used with those forms
- Migrate patch for Project/Task/Timesheet/Timesheet Detail/ToDo custom fields required by the ported scripts
- Patch to disable superseded site Client Scripts after deploy

---

## 0.2.34 — 2026-08-05

### Added

- Consolidated 24 Frappe Cloud custom DocTypes into Opero as standard module DocTypes (budget/spend, time allocation, WASH/personnel, and related child tables)
- Ported enabled Form Client Scripts for those DocTypes into `public/js/custom/`
- Server Script fixtures for Auto Share Records, Chart in Project Budget, Full Name, Get Project Master Managers, and Holidays Fetch
- Travel Request custom fields (accommodation, mileage, per diem, project) via migrate patch when HRMS is installed
- Patch to mark former site DocTypes as app-owned (`custom=0`) and disable superseded Client Scripts

---

## 0.2.33 — 2026-07-09

### Changed

- Replaced machine-specific AI rule references with portable bench-relative paths.
- Documented Opero-specific rule precedence against bench-wide guidance.

---

## 0.2.32 — 2026-05-11

### Added

- Focus chip as the default landing tab with a priority-scored algorithm (overdue+active → overdue → today+active → today → active → stale)
- Closed tab showing todos closed in the last 30 days with lazy fetch, reopen action, and a 100-item cap with overflow footer
- Search box in the page header (press `/`) with cross-tab routing — results show which tab the todo lives in and open its detail panel there
- Keyboard navigation in the queue list (ArrowUp/Down to move, Enter to open)
- Undo toast (4-second window) for mark-done, remove assignee, and clear project actions
- Sparkline hover tooltips showing date and count for each day
- Stale items included in the Focus tab at the lowest priority tier
- Priority dropdown now shows colour-coded rows with a left-border accent and a "No priority" clear option
- Project field displays `project_name` instead of the project ID; search works by both name and ID; resolved names are cached client-side

### Changed

- Health chip shows a directional arrow (↑/↓/→) to the right of the label instead of a numeric value
- Items departing a filtered list now linger briefly with a fade-then-collapse exit animation instead of disappearing instantly
- Save refresh is silent — no loading skeleton flash while the server round-trip completes
- Detail panel context is preserved across silent refreshes so the panel does not jump or reload
- Selected list item hides the due pill and avatars (already shown in the detail panel)
- Risk rows in the Health tab now navigate to the matching tab within Flow Hub instead of leaving to the List view
- Section labels in the detail panel use a more muted tinted colour to recede behind content
- Input fields show a grey background on focus with no border highlight, consistent with Frappe form styling
- Tab switches animate with a 120ms fade
- Sparkline colours use CSS variables (`--fh-positive`, `--fh-negative`, `--fh-neutral`) for theme compatibility
- Activity section shows a shimmer skeleton while loading instead of plain text

### Fixed

- Contextual empty state messages per tab (e.g. "Nothing overdue." instead of generic "All clear.")
- Due date picker opens at the existing due date's month rather than always defaulting to the current month

---

## 0.2.30 — 2026-05-07

### Changed

- Extended the outlined legend-border field design to description, attachments, and extra fields in the Flow Hub detail panel.
- Description field now toggles between rendered view and inline edit mode within the same outline.
- Attachments redesigned as an outlined field with file chips matching the Assignee(s) pattern; remove button hidden until chip is hovered.
- Extra fields (Reference Type/Name, Role, Assignment Rule, Color, Sender) exposed inline in the panel; link fields use combobox, data fields use inline text input; empty fields hidden behind a toggle by default.

### Fixed

- Fixed Beneficiary field to use `assigned_by` instead of the non-existent `custom_owner`.

---

## 0.2.29 — 2026-05-07

### Changed

- Redesigned Flow Hub detail panel with a Members section (Creator, Beneficiary, Assignees) and combobox-based link fields.
- Project field uses outlined legend-border design with inline combobox search.
- Members section shows Creator (read-only), Beneficiary (combobox), and Assignee chips with main-assignee diamond marker and promote/remove interactions.
- Status bar tab style updated to underline pattern matching Frappe form-tabs; removed chip icons and fixed last-updated wrapping at narrow widths.
- Backend now exposes `creator_name` and `beneficiary_name` from `get_todo_detail_context`; uses `custom_short_name` (reyal_core) for all user display names where available.

### Fixed

- Fixed description field rendering raw HTML (Quill content) instead of rendered output.

---

## 0.2.28 — 2026-05-06

### Changed

- Consolidated AI working rules into `AGENTS.md` as single source of truth; `CLAUDE.md` now redirects there.

---

## 0.2.27 — 2026-05-06

### Changed

- Expanded Flow Hub detail interactions with in-panel editing for description, project reference, attachments, comments, and additional metadata fields.
- Replaced the detail `Tags` section with a dedicated `Project` selector that auto-sets `reference_type = Project` when a project is chosen.
- Refined detail actions and density by removing redundant top-bar assignment controls and detail-panel avatars.
- Limited slide-over detail behavior to mobile widths only, while keeping tablet/desktop in split layout mode.
- Restyled the due-date popover/calendar using Frappe CSS tokens and simplified Today/Tomorrow shortcut labels.

### Fixed

- Fixed activity timestamp rendering so relative times display as plain text instead of escaped HTML fragments.

---

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
