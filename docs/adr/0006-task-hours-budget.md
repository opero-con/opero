# ADR-0006: The Task's Hours Budget caps each person's allocations

- **Status:** Accepted
- **Date:** 2026-09-29
- **Affects:** Task, Task Allocation
- **Supersedes:** removing the Task's Time Allocation table in [ADR-0005](0005-task-allocation.md)

## Context

ADR-0005 made Task Allocation the only allocation record and derived the task's allocated hours from it. That removed the ceiling the Task used to set: Task Time Distribution could not spread more hours than the person's total on the Task.

## Decision

- The Task's per-person table is shown again as **Hours Budget** (Task Time Allocation, `custom_time_allocation`). Budget Hours is a limit set by the project manager, not an allocation; allocations never change it.
- One budget row per person. **Committed** is read-only: the hours in the person's submitted Task Allocations. **Overrun** is read-only and always equals Committed less Budget Hours, never below zero (an hours overrun), so Committed = Budget Hours + Overrun whenever there is an overrun. Both are recalculated when an allocation is submitted or cancelled and when the Task is saved.
- Submitting an allocation that causes or grows an overrun is not blocked; it warns on the ribbon and on submit. Raising the budget to cover the allocations clears the overrun.
- Submitting an allocation for a person with no budget row on the task is refused; a zero-hour row still counts as a budget. A person with submitted allocations keeps their row: it cannot be removed from the Task.
- Overruns show in orange in the budget table and in the allocation grid's Budget column.
- The migration records each person's committed hours and overrun without changing budgets, adding zero-budget rows for existing allocations that have none.

## Consequences

- Budget changes are in the Task's version history; overruns are visible on the row until the budget is raised or allocations are cancelled.
- A budget can be lowered below submitted allocations; the difference shows as an overrun.
- Hours are the stored budget unit. **Budget Days** can be typed instead and converts at HR Settings standard working hours; days are recalculated from hours on save.
- **Distribute** on a budget row spreads the unplanned budget (budget less submitted and draft allocations) across every month of the task, weighted by each month's available hours (evenly when the Holiday List does not cover every month), and creates draft allocations for review.
- The Time Allocation table is kept in the follow-up cleanup; only Task Time Distribution is removed.
