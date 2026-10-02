# ADR-0007: Deploy one record at a time

- **Status:** Accepted
- **Date:** 2026-10-02
- **Affects:** Opero Site DocTypes, Employee, Enterprise, Partner, Deploy Center
- **Supersedes:** the batch-only Deploy in [ADR-0004](0004-publish-checkbox-and-statuses.md)

## Context

Deploy to website sent every queued change. A record left in To publish by mistake, for example by a trainee, went live with the next unrelated deploy.

## Decision

- Each queued record has a **Deploy** button for users who can deploy. It deploys that record only, after a review of the files it changes.
- A record's deploy covers its content file, the media that file uses, and the old file a rename left on the site. The pending cache records which record owns each old file.
- Every other pending change keeps its GitHub version and its status. A selective deploy prunes only media that the deployed files used before and no remaining file uses.
- The server enforces the selection: `planned_content_changes(paths=...)` is the one place that decides what a deploy writes.

## Consequences

- Deploy Center's Deploy to website still sends every queued change until it gains its own selection.
- If the pending cache is cleared before a renamed record is deployed, its old file is no longer tied to the record. Deploy Center still lists that file for deletion.
