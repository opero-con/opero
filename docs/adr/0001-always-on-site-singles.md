# ADR-0001: Home Page, Privacy, and Site Settings are always on-site

- **Status:** Accepted
- **Date:** 2026-08-30
- **Affects:** Cubenet Opero Site DocTypes (`opero`), publish status, Deploy Center

## Context

Show on website was added to every Opero Site DocType so Cubenet could queue
publish and unpublish without editing the hidden Status field. That control
belongs on optional records: Publication, Team Member, and Home Page partner
rows.

Home Page, Privacy, and Site Settings are the public site itself. Unchecking
Home Page never took `/` down: `home.md` is not in the managed-delete prefixes,
so deploy skipped the write and GitHub kept the last published file. The
checkbox looked like an off switch and was not one.

## Decision

Home Page, Privacy, and Site Settings have no Show on website field. They are
always on-site. Status is still the title pill (`To publish` / `Published`).
Load from GitHub and Publish to website keep writing their Markdown whenever
the record has the required copy.

Publication, Team Member, and partner rows keep Show on website.

## Consequences

- Do not add Show on website back onto those three singles.
- A Home Page save cannot queue Draft or To unpublish.
- Taking the homepage, privacy page, or site chrome off the public site is a
  product decision that needs a new record, not a checkbox.

## Alternatives considered

**Keep the checkbox, default it on, and hide it.** Rejected: the field still
drives status, and a Custom Field or form customize could show it again.

**Delete `home.md` when Home Page is unchecked.** Rejected: `/` would 404 or
fall back to seed copy. That is not an editorial toggle.
