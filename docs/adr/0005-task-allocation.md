# ADR-0005: Task Allocation is the monthly allocation record

- **Status:** Accepted
- **Date:** 2026-09-29
- **Affects:** Task, Timesheet, Project, allocation reports
- **Supersedes:** Task Time Distribution as the allocation source in [ADR-0001 (timesheets)](0001-timesheet-balances-and-sync.md)

## Context

Allocations lived in two places: a per-person total on the Task (Task Time Allocation) and a monthly spread in Task Time Distribution. Timesheets were checked against the spread, but project managers edited the total, and a raised total landed in the month of the edit. The two drifted apart on 178 of 543 live records.

## Decision

- **Task Allocation** holds one employee's hours on one task for one month (Month, Year, and a derived Month Start). It is the only place allocation hours are entered.
- Task Allocation is submittable. Only submitted records count: timesheet budgets, task and project allocated hours, the Task grid, capacity, and reports. Hours change by cancel and amend.
- Several submitted records may exist for the same task, employee, and month; a top-up is its own record. The form warns on the ribbon when earlier allocations exist.
- Cancelling is refused when it would leave less allocated than the employee has submitted on timesheets for that task and month.
- Task `custom_total_hours` and Project `custom_allocated_hours` are derived from submitted Task Allocations.
- Available time for a month uses the Weekly Hours rule: working days from the employee's (or company's) Holiday List, less Attendance leave, times HR Settings standard hours. It is unknown without a covering Holiday List, and for part-time staff. Going over warns on submit and never blocks.
- The migration copies monthly rows as submitted allocations. Monthly rows win over task totals; a total with no monthly rows lands in the task's end month.

## Consequences

- Task Time Distribution is read-only and its data is frozen. Its DocTypes and the Task's hidden Task Time Allocation fields are removed in a follow-up once live is verified.
- Saved reports read Task Allocation through subqueries that keep the old column names, so their layouts did not change.
- Capacity is only as accurate as the Holiday Lists: they must list weekly offs and cover the months being planned.
