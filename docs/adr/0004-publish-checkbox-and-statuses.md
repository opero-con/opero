# ADR-0004: Publish checkbox and five website statuses

- **Status:** Accepted
- **Date:** 2026-09-25
- **Affects:** Opero Site DocTypes, Employee, Enterprise, Partner, Deploy Center
- **Supersedes:** the status names in [ADR-0001](0001-always-on-site-singles.md)

## Context

Optional site records had a **Show on website** checkbox and the statuses Draft, To deploy, Published, To unpublish, and Unpublished. Every Desk save of a ticked record, and of an always-on page, set **To deploy**, so the pill could not tell a record going live for the first time from an edit to a live one. Unpublished and Draft both meant "not on the site".

## Decision

- The checkbox is labelled **Publish**. Its fieldname stays `show_on_website`.
- Statuses are **Draft**, **To publish**, **To update**, **Published**, and **To unpublish**.
- Draft means the record is not on the site: never live, or taken down.
- Ticking Publish gives To publish, or To update when the saved status is live (To update, Published, To unpublish).
- Unticking gives To unpublish when live, otherwise Draft.
- Always-on pages go to To update on every Desk save.
- After a deploy, To publish and To update become Published, and To unpublish becomes Draft.
- **Publish** names the per-record choice; **Deploy** stays the name of the batch action that carries it out.

## Consequences

- A hidden employee, enterprise, or partner file (`active: false`) stays on GitHub as a Draft record's kept file.
- Whether a Draft record was ever live is only in its version history.
- The migration patch asks GitHub which queued records are visible to split To deploy into To update and To publish. Without a token it uses To update, which is safe to redeploy.
