# Standard Working Hours is a reference, not a Timesheet daily cap

- **Status:** Accepted
- Supersedes the Standard Working Hours daily cap in ADR-0010 and ADR-0012.

The director has approved recording more than the standard working day. Timesheet preview, save, and submission no longer reject an employee's daily total because it exceeds HR Settings Standard Working Hours. That field stays in HR Settings and remains available to capacity calculations, reports, and other scripts. Timesheet scheduling does not require it to be populated.

Timesheet starts at still controls generated timestamps. Entries must fit within the selected work date, avoid other active entries, and satisfy the existing monthly Task Allocation and submission checks. Approved history is not rewritten. This decision removes the standard-hours cap; it does not change the work-date boundary or monthly budgets.
