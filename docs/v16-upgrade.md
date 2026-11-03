# Opero Frappe v16 preparation

This compatibility branch targets Frappe `>=16.54.0,<17.0.0` and Python 3.14+.
Use Node 24+ for assets. It is not an update to install on the v15 bench.

## Frappe Cloud target apps

Keep all six production apps: Frappe, ERPNext, Payments, HRMS, Opero and
Reyal Core. Add `frappe/newsletter` on its supported v16 source before Opero
installation or migration. Opero declares Newsletter as a new
prerequisite. Select v16-compatible sources for each app through FC.
Reyal Core already has a separately prepared `fix/v16-compatibility` branch;
its v15 `main` must not be carried into the v16 target by accident.

## Query and test migration

Allocation capacity, task budget/distribution/grid queries, timesheet totals and
historical migration helpers use v16 aggregate dictionaries instead of SQL
function strings in `fields`. Aliases and permission-aware query selection are
retained. Test fixtures use v16's Holiday List Assignment records and link
validation API; the legacy controller test supplies metadata now inspected by
the framework loader.

## Validation

Run the database-free regression suite with Frappe v16, HRMS and Newsletter
available on the Python path:

```sh
python -m unittest discover -s tests -v
node --test opero/tests/*.test.js
```

Also install both custom apps on an isolated v16 site, run normal migration
with fixtures enabled, clear cache and build Opero/Reyal assets. Exercise
mailing lists, signup/unsubscribe, recipient eligibility, Website hiding for
staff and visibility for administrators, and Opero's existing integration tests.
Block external mail, Zoho and website publication during validation and leave
scheduler workers stopped.

Before production clearance, rehearse a recent FC backup including files and
inspect site-owned scripts, custom fields, workflows and print formats. Perform
business acceptance for timesheets, allocations, leave/travel, reports and
publication workflows. Review FC backup/rollback and app source revisions
before the separately authorized production upgrade.

## Branch delivery and validation status

Keep `fix/v16-compatibility` separate from v15 `main`. Configure the v16 FC
bench to use this branch; do not merge this port into the branch serving v15.
This is a compatibility preparation branch, not production upgrade clearance.

Validated on 3 November 2026 with Frappe 16.54.0, ERPNext 16.53.0,
HRMS 16.52.0, Python 3.14, Node 24 and the standalone Newsletter app:

- Five database-free compatibility tests passed, including 332 module imports.
- All 82 focused allocation, timesheet, weekly-hours and legacy migration tests passed.
- Six standalone JavaScript test files passed.
- Installation, full migration with fixtures, cache clear, both custom-app asset
  builds, package builds and real Desk boot passed on an isolated synthetic site.
- Changed Python files passed lint and formatting.
- Broader Opero suite: 398 tests, 315 passes, eight failures, 74 errors, one skip.
  Failures remain around site metadata/defaults, media fixtures, existing
  duplicate-email rules and older test expectations. They are not all proven
  environmental or pre-existing and must be investigated before deployment.
- Whole-repository lint retains 35 findings, versus 37 on the starting main;
  comparison found no new findings.

The available Reyal Core v16 branch passed seven Python tests, its notification
JavaScript test, whole-repository lint and formatting, and native v16 boot/name
patch checks. Production backups and Payments were not part of the synthetic
custom-app rehearsal. No application server or scheduler workers were started,
so application restart was skipped. Production was not changed.

## Desk navigation

The v16 branch ships an Opero app entry, two standard Sidebars and an app Dock.
The Opero sidebar opens the existing Opero workspace, followed by Approvals and
the Time, Requests, Budgets, Partners & Contracts and Setup links. Site Content
opens the existing Site Content workspace and its content-management links.
Native Frappe permissions filter each user's available destinations; these files
do not grant roles or access to records. Site and user navigation arrangements
remain in Frappe's customization layers.

Navigation documents are authored on a local v16 developer site and exported by
Frappe, rather than maintained as runtime hooks. A normal migration imports them.
The app entry opens `/desk/opero`; `/desk/site-content` opens Site Content directly.
The Desktop Icon export also supplies the Opero entry for sites using the icon grid.
No migration or production navigation change is executed by preparing these files.

Navigation validation on the isolated v16 site: native migration/import and
real boot-payload checks passed. The workspace suite ran 16 tests: 12 passed,
two failed and two errored, matching the failures in the pre-change full-suite
log (missing module on two fixtures, missing Travel Request approval field, and
a stale Blogger-role expectation). The apps-screen hook passes Ruff lint and
format checks. No JS/CSS changed, so asset build is not required. No app server
or workers run on the isolated site, so process restart is not applicable.
