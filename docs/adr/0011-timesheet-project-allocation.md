# Timesheet Project selection follows personnel allocations

- **Status:** Accepted

The main Timesheet Project is compulsory. Selecting Personnel restricts the Project picker to projects with a positive submitted Task Allocation for that employee in any month. The Task's current Project determines membership; the allocation's cached Project field is not authoritative. Project read permissions and an existing customer filter still apply. Without Personnel the picker has no choices.

The same eligibility rule is enforced on save, including API and import saves. It establishes project eligibility only: the existing monthly Task Allocation check still enforces the particular Task, work month, and available hours. Draft, cancelled, and zero-hour allocations do not establish eligibility. Existing approved timesheets and historical data are not rewritten.
