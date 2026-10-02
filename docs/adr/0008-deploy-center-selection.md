# ADR-0008: Deploy Center deploys only the selected changes

- **Status:** Accepted
- **Date:** 2026-10-02
- **Affects:** Deploy Center, Opero Site DocTypes, Employee, Enterprise, Partner
- **Supersedes:** Deploy to website in [ADR-0007](0007-per-record-deploy.md)

## Context

After ADR-0007 a record could deploy alone from its form, but Deploy Center's Deploy to website still sent every queued change, so a change queued by mistake still went live with the next Deploy Center deploy.

## Decision

- Each pending file in Deploy Center has a checkbox, unchecked by default. **Deploy selected** replaces Deploy to website.
- The server adds the other half of a rename to the selection, shows the resulting changes for review, and deploys only those.
- Only records behind the deployed files change status. Every other pending change keeps its GitHub version and status.
- The server has no deploy-everything entry point: `commit_planned_changes` requires the selected paths.

## Consequences

- Deploying everything means checking every row. There is no Select all, so each change is chosen on purpose.
- Refresh (the GitHub compare) still lists every difference between Desk and the website.
