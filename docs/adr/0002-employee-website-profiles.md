# ADR-0002: Publish website team profiles from Employee

- **Status:** Accepted
- **Date:** 2026-09-12
- **Affects:** Employee, Opero Site publishing and loading, Deploy Center

## Context

Opero previously stored a second person record in Team Member for each employee
shown on the public website. The duplicate identity and portrait fields could
drift from ERPNext's Employee record and required administrators to maintain the
same person in two places.

## Decision

Employee owns the optional website profile in a Website tab. Opero adds role,
ordering, LinkedIn, publishing state, and an optional separate portrait. The
standard Employee image is used by default. Slug and portrait alt text are
derived from the Employee name and are not editable.

The public content contract remains `content/team/{slug}.md`, so opero-content
and opero-site require no coordinated schema change. Loading team Markdown
updates a uniquely matching Employee by slug or exact employee name and never
creates an Employee. Existing Team Member records migrate only where exactly one
Employee has the same employee name; migration stops before writing when any
record is missing or ambiguous.

Employee's HR status remains independent from the website publishing status.
The standalone Team Member DocType is removed after a successful migration.

## Consequences

- Administrators maintain one person record and opt it into the website.
- Website editors need the existing ERPNext permission to read and edit Employee;
  Opero does not grant broad Employee access to Website Manager.
- Renaming an Employee changes the derived slug and therefore the content path on
  the next deploy.
- Legacy portrait crop and scale controls are no longer emitted.

## Alternatives considered

**Keep Team Member linked to Employee.** Rejected because it preserves duplicate
records and two editing surfaces.

**Create Employees while migrating or loading content.** Rejected because public
content does not contain the HR fields required to create a valid Employee safely.
