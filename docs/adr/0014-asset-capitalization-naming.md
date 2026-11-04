# ADR-0014: Asset Capitalization identifiers use the initial posting month

- **Status:** Accepted
- **Date:** 2026-11-04
- **Affects:** New Asset Capitalization documents on sites with Opero installed

## Context

Frappe's `YY` and `MM` naming tokens use the creation date. A capitalization
entered in November for a July purchase therefore receives a November identifier,
which makes backdated entries harder to identify.

## Decision

- Name new Asset Capitalizations `ASC-YYMM<number>` from the posting date at
  creation, using Frappe's standard counter for each year and month. For example,
  the first July 2026 capitalization is `ASC-26071`.
- Apply this only to Asset Capitalization; other document naming is unchanged.
- Keep identifiers fixed after creation, including when a draft's posting date
  changes. Existing capitalizations are not renamed.
- Preserve Frappe's amendment naming rules and existing monthly counters.
- Keep the displayed naming series as `ASC-.YY.MM.#`; Opero's `autoname` event
  supplies the posting-date prefix instead of the standard creation-date tokens.

## Consequences

- All companies on a site share the counter for a posting month.
- An identifier shows the posting month chosen at creation, not necessarily the
  current posting month after a subsequent date correction.
- Deployment does not rename existing records or reset naming counters.
