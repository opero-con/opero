# Generated timesheet start in HR Settings

- **Status:** Accepted
- Updates ADR-0010's fixed 08:00 start policy.

HR Settings owns Timesheet starts at, next to Standard Working Hours. It defaults
to 08:30 and controls both preview and save. Standard Working Hours remains the
source of the combined daily hours limit.

Each task entry keeps its existing row and hours. Generated timestamps describe
continuous task-hour slots and do not insert lunch or split rows. A seven-hour
entry starting at 08:30 therefore ends internally at 15:30. These timestamps are
not evidence of attendance or an early departure.

Other active logs still reserve their intervals. Approved and cancelled records
are not rescheduled, and this change does not rewrite existing timesheets.
Changes to the start time apply when unapproved logs are next generated.

Future attendance retains actual clock-in/out independently and can be linked
by employee and work date. Attendance integration is deferred.
