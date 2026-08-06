# Entity Scoping

Opero runs more than one legal entity in a single site. This document describes
how a project's entity reaches everything beneath it, and how people are given
access across entities.

An **entity** is an ERPNext **Company**. No entity is named anywhere in this
repository: every rule is derived from the Company records on the site, so
entities can be added, renamed or retired without a code change.

---

## The rule

`Project.company` is the single source of truth. Every document linked to a
project belongs to that project's entity — the entity that bears the cost of the
work — regardless of who does the work.

Cross-entity staffing is normal and supported: an employee of entity A may be
booked onto entity B's project. The document then belongs to **B**. Access is
granted separately, through Company User Permissions.

---

## How it is enforced

Three layers, each of which is sufficient on its own for the case it covers:

| Layer | Where | What it does |
|---|---|---|
| Fetch | DocType `fetch_from` | Copies `project.company` into the document |
| Form | `public/js/custom/entity_scope.js` | Company follows the project as you type, then locks; link pickers only offer same-entity records |
| Server | `opero/entity.py` (`validate` hook) | Re-derives the company on every save and refuses anything that disagrees |

The server layer is the authority. The form layer exists so the switch is visible
while the user is still filling the form in — company-dependent fields such as
accounts, cost centres and currency need the right entity before the save, not
after.

### What is scoped

Two registries in `opero/entity.py` decide this, and they are the only place the
list lives — `hooks.py` wires the dispatcher once for every DocType:

* `PROJECT_SCOPED_DOCTYPES` — company comes from the project. Covers Opero's own
  Budget Line, Cash Advance-Reimbursable Form, Consultant Task, Project Budget,
  Project Time Allocation, Task Time Distribution and Actual Spend, plus the
  standard Task, Timesheet, Travel Request, Expense Claim, Material Request,
  Activity Type and Activity Cost.
* `EMPLOYEE_SCOPED_DOCTYPES` — company comes from the employee, because the
  document describes a person rather than a project: Work Hours Summary and
  Contract Documents. These are stamped so User Permissions can filter them at
  all; without a company field they would be visible to everyone.

Adding a DocType to a registry is all that is needed to enforce it.

A DocType reaches its project either directly (`project`, `parent_project`,
`custom_project`) or through another document — Actual Spend reads its entity
from its Cash Advance, Activity Cost from its Activity Type.

### Where the field appears

| DocType | Field | On the form |
|---|---|---|
| Opero's project-linked DocTypes | new `company` | Directly below the project, read-only |
| Actual Spend | new `company` | Below `cash_advance`, read-only |
| Work Hours Summary, Contract Documents | new `company` | Below `personnel`, read-only |
| Activity Type, Activity Cost | new `custom_company` | Below `custom_project` / `activity_type`, read-only |
| Task, Expense Claim, Material Request | ERPNext's own | Where ERPNext puts it; locked once a project is set |
| Timesheet, Travel Request | ERPNext's / HRMS's own | Where they put it; locked once a project is set |

Timesheet and Travel Request were hidden while the site ran a single company.
They are unhidden, because they are the two forms where cross-entity work
actually shows up — someone employed by one entity logging time or travel
against another entity's project — and the field decides which entity bears the
cost. Hiding it also hid the fact that picking a project can move the document,
and its currency, into the other entity's books.

HRMS fetches `Travel Request.company` from the employee. Frappe applies
`fetch_from` before `validate`, so the project still wins.

Both stay visible-but-locked rather than permanently read-only, so a document
with no project keeps whatever company it would have had before.

### Documents may not span entities

Where a document has child rows carrying their own project (Timesheet time logs,
Expense Claim expenses, Material Request items), every row must resolve to the
same entity as the parent. A row pointing elsewhere is rejected on save.

### Submitted documents

While a document is a draft, the project wins: change the project and the company
follows. Once it is submitted its entity is fixed — the document is already in
that entity's ledger, so moving it silently would rewrite history. Cancel and
amend instead.

### Changing a project's entity

A project's company can be changed freely while nothing hangs off it. As soon as
any document exists under the project, the change is refused and the blocking
documents are listed. Remove or cancel them first.

---

## Display name

A Company is named after its registered legal name — right for invoices and the
ledger, but long and near-identical between entities in every link field, filter
and report column.

Each Company therefore carries a **Display Name**. Frappe renders it in place of
the stored name wherever a link appears — form fields, link dropdowns, list views
and report columns all run through the same formatter — and falls back to the
registered name when it is blank. Nothing about what documents record changes.

Set it on the Company record. It is data, not configuration: the names live on
the site, not in this repository.

The registered name still appears where it should: on the Company form itself,
in print formats, and in anything reading `Company.company_name`.

Note this is separate from the abbreviation. Numbering below uses `Company.abbr`,
which ERPNext also embeds in every Account and Cost Center name and marks
`set_only_once` — changing it is a chart-of-accounts operation, not a relabel.

## Numbering

Documents carry their entity's abbreviation, and each entity keeps its own
counter:

| DocType | Example |
|---|---|
| Budget Line | `<ABBR>-1.1-Personnel` |
| Cash Advance-Reimbursable Form | `<ABBR>-CA-2632-0001` |
| Consultant Task | `<ABBR>-CT-2608-0001` |
| Project Budget | `<ABBR>-PROJ-0002/2026/01` |
| Project Time Allocation | `<ABBR>-TA-<first name>-0826-0001` |
| Task Time Distribution | `<ABBR>-TTD-2608-0001` |

Existing documents keep the names they already have; only new ones are prefixed.

Budget Line needs this most: a budget code such as `1.1 Personnel` is only unique
inside one entity, and both entities can run one.

A document saved before its project is known falls back to the DocType's own
`autoname`, so nothing fails for want of an entity.

---

## Giving someone access to another entity

Frappe's rule is easy to get wrong by hand:

* a user with **no** Company User Permission sees **every** entity;
* a user with **one or more** sees **only** those.

So granting access to a second entity means also holding one for their own —
otherwise "adding" access silently removes it everywhere else.

Use **Entity Access** (`/app/entity-access`, System Manager only). Tick the
entities a person may see; the page writes the Company User Permissions,
`apply_to_all_doctypes` included, and shows an "all entities" badge for anyone
who is currently unrestricted. Clearing every tick restores unrestricted access.

The same thing can be done by hand under User Permissions; the page exists
because the "no permission means everything" rule catches people out.

---

## Reporting

Every Opero report takes an optional **Company** filter. Dynamic Timesheet, Used
Hrs Summary, ToDo Explorer and ToDo In Progress Aging also carry a Company
column.

A ToDo has no company of its own — it inherits one from whatever it references,
so filtering ToDo reports by entity keeps only ToDos pointing at a document in
that entity. ToDos referencing nothing, or something outside the registries, drop
out.

---

## Backfill

`opero.patches.v0_3.backfill_entity_company` stamps each project's **existing**
company onto the documents beneath it. Nothing is reassigned — projects keep
whatever entity they already have. It is written as set-based SQL so `modified`
does not move and submitted documents are stamped too, and it is safe to re-run.
