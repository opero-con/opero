# Architecture decision records

One file per decision, numbered in the order they were taken:
`NNNN-short-slug.md`. Never renumber or rewrite a record once it is merged — a
decision that no longer holds gets a new record that supersedes it, and the old
one is marked `Superseded by ADR-NNNN`.

Write a record when a decision **constrains future work** or **replaces an
earlier decision**. Do not write a record for ordinary implementation choices
that the commit message already explains.

| ADR | Decision | Status |
|-----|----------|--------|
| [0001](0001-always-on-site-singles.md) | Home Page, Privacy policy, and Site Settings are always on-site | Accepted; status names superseded by ADR-0004 |
| [0002](0002-employee-website-profiles.md) | Publish website team profiles from Employee | Accepted |
| [0003](0003-standalone-website-partners.md) | Publish website partners as standalone records | Accepted |
| [0004](0004-publish-checkbox-and-statuses.md) | Publish checkbox and five website statuses | Accepted; batch-only Deploy superseded by ADR-0007 |
| [0005](0005-task-allocation.md) | Task Allocation is the monthly allocation record | Accepted; Time Allocation removal superseded by ADR-0006 |
| [0006](0006-task-hours-budget.md) | The Task's Hours Budget caps each person's allocations | Accepted |
| [0007](0007-per-record-deploy.md) | Deploy one record at a time | Accepted |
| [0008](0008-deploy-center-selection.md) | Deploy Center deploys only the selected changes | Accepted |
| [0009](0009-publication-ids.md) | Publication IDs are independent of slugs | Accepted |
| [0010](0010-timesheet-daily-times.md) | Retrospective timesheet dates and daily hours | Accepted; daily cap superseded by ADR-0013 |
| [0011](0011-timesheet-project-allocation.md) | Timesheet project allocation | Accepted |
| [0012](0012-timesheet-schedule.md) | Generated timesheet start in HR Settings | Accepted; daily cap superseded by ADR-0013 |
| [0013](0013-timesheet-hours-reference.md) | Standard Working Hours is a reference, not a Timesheet daily cap | Accepted |
