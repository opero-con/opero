# ToDo Dashboard Implementation Spec (Opero)

## 1. Objective
Build a production-ready ToDo dashboard for Opero that gives users an immediate action view (what needs attention now) and a performance view (how work is moving over time), aligned with current ToDo customizations in this app.

## 2. Current Baseline (Already in Opero)
This spec assumes the existing ToDo enhancements are active:
- `custom_title` as primary user-facing title
- `custom_assignees` (Table MultiSelect via `ToDo Assignee` child table)
- status values include `In Progress`
- lifecycle timestamps: `custom_closed_on`, `custom_cancelled_on`
- due-date relational messaging already handled in `opero/public/js/todo.js`

## 3. Scope
### 3.1 MVP Scope (Phase 1)
Deliver a dashboard that answers:
- What should I do now?
- What is overdue or at risk?
- Are we closing ToDos on time?
- Who is overloaded?

### 3.2 Out of Scope (Phase 1)
- Kanban drag-and-drop board
- Cross-doctype portfolio rollups
- Notification engine redesign
- Mobile-specific custom page (workspace remains responsive default)

## 4. UX and Information Architecture
Implement one workspace: **`ToDo Command Center`** with two sections.

### 4.1 Section A: Action Center (Top Priority)
Components:
- Number Cards:
  - `My Overdue`
  - `Due Today`
  - `In Progress`
  - `Unassigned (Open + In Progress)`
- Table Report: `ToDo Action Queue`
  - Default sort: overdue first, then due today, then priority
  - Columns: Title, Status, Priority, Due Date, Assignees, Created By, Age (days)
- Quick Actions:
  - `New ToDo`
  - `My ToDos`
  - `Team ToDos`
  - `Overdue ToDos`

### 4.2 Section B: Performance
Components:
- Line chart: `Created vs Closed (Last 30 Days)`
- Donut chart: `Open vs In Progress vs Closed vs Cancelled`
- Number Card: `On-time Close Rate (30d)`
- Number Card: `Avg Closure Delay (days, 30d)`
- Table Report: `Assignee Load & Risk`

## 5. Functional Definitions
### 5.1 Status Buckets
- Active: `Open`, `In Progress`
- Done: `Closed`
- Dropped: `Cancelled`

### 5.2 Time Logic
- Overdue: active ToDo with `date < today`
- Due Today: active ToDo with `date == today`
- On-time closure: `status in (Closed, Cancelled)` and status timestamp date `<= due date`
  - Closed uses `custom_closed_on`
  - Cancelled uses `custom_cancelled_on`
- Closure delay days:
  - `0` if closed/cancelled on due date
  - negative if before due date
  - positive if after due date

### 5.3 Assignee Logic
- Primary assignee source for aggregation:
  - `allocated_to` for compatibility and speed
- Display assignees in report output:
  - include `custom_assignees` expanded as comma-separated IDs

## 6. Technical Design (Frappe v15)
Use standard Frappe artifacts first (no custom desk frontend in MVP):
- Workspace
- Script Reports / Query Reports
- Dashboard Charts
- Number Cards

### 6.1 New Artifacts
Recommended app paths:
- `opero/opero/report/todo_action_queue/`
- `opero/opero/report/todo_created_vs_closed_30d/`
- `opero/opero/report/todo_assignee_load_risk/`
- `opero/opero/workspace/todo_command_center/`
- `opero/opero/dashboard_chart/` (if charts are app-owned JSON docs)
- `opero/opero/number_card/` (if cards are app-owned JSON docs)

### 6.2 Report Specs
#### A) `ToDo Action Queue` (Script Report)
Purpose: operational worklist.

Filters:
- `assignee` (Link User)
- `status` (MultiSelect)
- `priority`
- `from_date`, `to_date`
- `show_only_overdue` (Check)

Default behavior:
- If no assignee filter, show current user’s assigned + created active ToDos
- Include done/cancelled only when explicitly filtered

Output columns:
- ToDo (Link)
- Title (`custom_title` fallback to plain text from description)
- Status
- Priority
- Due Date
- Due Context (text label from backend logic)
- Assignees
- Created By (`custom_created_by` fallback `owner`)
- Age Days

#### B) `ToDo Created vs Closed 30d` (Script Report)
Purpose: trend dataset for line chart.

Output by day:
- `date`
- `created_count`
- `closed_count` (includes Closed + Cancelled, or split optional)

#### C) `ToDo Assignee Load & Risk` (Script Report)
Purpose: team balancing.

Per assignee:
- active_count
- overdue_count
- due_today_count
- high_priority_active_count
- closed_7d
- on_time_rate_30d

### 6.3 Reusable Python Service Layer
Add a new module:
- `opero/todo_dashboard.py`

Responsibilities:
- shared date and status classification helpers
- report query builders
- due-context string formatter shared with backend reports
- centralized definitions for active/done statuses

Note: keep this logic server-side so dashboard/report consistency does not depend on client script execution.

### 6.4 Workspace Layout
Workspace name: `ToDo Command Center`

Top order:
1. Number card row (4 cards)
2. Action Queue table report
3. Trend and status charts
4. Assignee risk table
5. Quick action shortcuts

## 7. Data, Permissions, and Performance
### 7.1 Permissions
- Respect native ToDo permissions and user-level assignment visibility.
- No permission bypass in report queries.

### 7.2 Performance Targets
- Action Queue load < 1.5s for 5k ToDos
- Aggregation reports < 2.5s for 30-day window

### 7.3 Query/Index Considerations
If needed after profiling, add indexes on frequently filtered fields:
- `tabToDo(status, date)`
- `tabToDo(allocated_to, status, date)`
- `tabToDo(custom_closed_on)`
- `tabToDo(custom_cancelled_on)`

## 8. Rollout Plan
### Phase 1 (MVP)
- Build 3 reports
- Build workspace
- Build 4 number cards + 2 charts
- UAT with real users

### Phase 2 (Enhancements)
- Saved filter presets by persona (Ops, Manager, Personal)
- Escalation widgets (stale in-progress > N days)
- Optional custom page for richer interactions

## 9. Local Validation Plan (Required Before Push)
1. `bench --site dev-v15.local migrate`
2. `bench build --app opero`
3. `bench restart`
4. Validate workspace loads and all widgets render
5. Validate filters and counts against list view samples
6. Validate permissions with non-admin user

## 10. Acceptance Criteria
- Dashboard is accessible from Desk as `ToDo Command Center`
- Number cards show correct counts for current user context
- Action Queue sorting and filters behave as defined
- Trend charts display 30-day data with no script errors
- Counts match equivalent list/report queries (within expected timing window)
- No regression to existing ToDo form behavior

## 11. Open Decisions (Need Product Confirmation)
- On-time metric should include `Cancelled` or only `Closed`
- Team-wide dashboard visibility scope for non-managers
- Default date window for trend charts (30 vs 14 vs 90 days)

## 12. Suggested Build Order
1. Backend helpers (`todo_dashboard.py`)
2. `ToDo Action Queue` report
3. Trend + assignee reports
4. Number cards and charts
5. Workspace assembly
6. Local UAT and polish
