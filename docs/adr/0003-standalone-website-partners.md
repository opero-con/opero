# ADR-0003: Publish website partners as standalone records

Status: Accepted

## Context

Partners were child rows inside the `Partners` singleton and were serialized
inside `content/homepage/home.md`. That made partner editing, list columns,
publication state, and change tracking inseparable from the homepage.

## Decision

`Partner` is a standalone DocType with its own website visibility and publish
status. Each record publishes to `content/partners/<slug>.md`, matching the
per-record Enterprise content contract. The public site assembles the partner
logo section from that collection rather than homepage frontmatter. Internal
Partner IDs use `P` followed by five random digits; allocation retries when a
generated ID already exists.

Existing child rows are promoted in place. Visible rows start as Published and
hidden rows as Unpublished so migration does not change the live selection.
The former `Partners` singleton is removed.

This supersedes ADR-0001 only where it describes partner rows as part of the
Home Page section model.

## Consequences

- Partners have an independent list view, permissions, ordering, and deploy lifecycle.
- Existing Partner records are renamed to the `P12345` identifier format during migration.
- Renaming a partner queues deletion of its old slug path.
- Loading website content upserts partners by derived slug or case-insensitive name.
- The homepage Markdown no longer owns or preserves a `partners` key.
