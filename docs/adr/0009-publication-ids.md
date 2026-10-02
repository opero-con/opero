# ADR-0009: Publication IDs are independent of slugs

- **Status:** Accepted
- **Date:** 2026-10-02
- **Affects:** Publication, website view counts, Load from website, Deploy Center

## Context

Publications were named by their slug (`autoname: field:slug`), so two publications with the same title clashed, and Frappe copied the name back into the slug on every save, so a slug could never change.

## Decision

- New publications are named `PUB-#####`. Existing publications keep their slug names, and their website URLs do not change.
- The slug stays unique and is the website URL. A blank slug comes from the title, numbered `-2`, `-3` when another publication has it; a typed slug that is taken is refused.
- A slug is fixed while the publication is live (To update, Published, To unpublish). Unpublish and deploy before changing it.
- Code that finds a publication from a website path or view count looks it up by `slug`, never by name.

## Consequences

- Duplicate titles are allowed.
- Because live slugs cannot change, a deploy never needs to remove a publication's old URL.
