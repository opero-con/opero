# Retrospective timesheet dates and daily hours

- **Status:** Accepted
- Supersedes the midnight splitting policy in ADR-0001.

Timesheets record a work date and duration rather than attendance clock times. From Time remains a datetime field; its date is the input and its clock time is generated. Before ERPNext validation, Opero places entries in free intervals from 08:00, preserving entries in other active timesheets. All entries in one timesheet must share a work date. A permission-checked server preview generates From Time and To Time when the work date, Hours, or employee changes in the form. Incomplete entries are skipped in the preview and validated on save. The same scheduler runs on save, including imports and API saves, so concurrent edits cannot bypass reservations.

HR Settings Standard Working Hours caps the employee's combined duration across drafts, pending approval, and approved timesheets for the date. Cancelled documents do not reserve time. Employee locks and locking reads serialize concurrent saves. Missing personnel, dates, positive hours, or HR configuration block saves. Entries cannot continue past midnight; an entry ending exactly at midnight belongs to its start day. Split at midnight is removed.

Previously approved documents are not rescheduled on subsequent updates or cancellation. Existing multi-day documents need manual review before editing or approval. This change does not rewrite historical data or establish attendance times.
