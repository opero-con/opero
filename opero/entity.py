"""Entity scoping — a Project's company owns every document that hangs off it.

Opero runs more than one legal entity inside a single site. `Project.company` is
the single source of truth for which entity owns a piece of work: every document
linked to that project inherits the same company, is shown read-only in the form,
and is re-derived from the project on every save.

Cross-entity staffing is allowed. An employee of one entity may be booked to
another entity's project — the document then belongs to the *project's* entity,
because that entity bears the cost. Access to the other entity's records is
granted through Company User Permissions (see `opero.api.entity_access`).

Nothing in this module names or identifies a specific entity. Every rule is
derived from the Company records on the site, so entities can be added, renamed
or retired without a code change.
"""

from __future__ import annotations

from typing import NamedTuple

import frappe
from frappe import _
from frappe.model.naming import make_autoname


class ProjectScope(NamedTuple):
	"""How a DocType reaches its owning Project, and where its company lives.

	project_field:        fieldname holding the Project link
	company_field:        fieldname holding the Company link
	via:                  (link fieldname, linked DocType) when the Project is
	                      reached indirectly, e.g. Actual Spend -> Cash Advance
	child_project_fields: (child table fieldname, Project fieldname on the row)
	                      pairs whose rows must not point at another entity
	"""

	project_field: str
	company_field: str = "company"
	via: tuple[str, str] | None = None
	child_project_fields: tuple[tuple[str, str], ...] = ()


#: Documents whose entity is dictated by their Project.
PROJECT_SCOPED_DOCTYPES: dict[str, ProjectScope] = {
	# Opero-owned DocTypes
	"Budget Line": ProjectScope("project"),
	"Cash Advance-Reimbursable Form": ProjectScope("project"),
	"Consultant Task": ProjectScope("project"),
	"Project Budget": ProjectScope("project"),
	"Project Time Allocation": ProjectScope("project"),
	"Task Time Distribution": ProjectScope("project"),
	"Actual Spend": ProjectScope("project", via=("cash_advance", "Cash Advance-Reimbursable Form")),
	# Standard DocTypes driven by Opero's project workflow
	"Task": ProjectScope("project"),
	"Timesheet": ProjectScope("parent_project", child_project_fields=(("time_logs", "project"),)),
	"Travel Request": ProjectScope("custom_project"),
	"Expense Claim": ProjectScope("project", child_project_fields=(("expenses", "project"),)),
	"Material Request": ProjectScope("custom_project", child_project_fields=(("items", "project"),)),
	"Activity Type": ProjectScope("custom_project", company_field="custom_company"),
	"Activity Cost": ProjectScope(
		"custom_project",
		company_field="custom_company",
		via=("activity_type", "Activity Type"),
	),
}

#: Documents that belong to the employee's own entity — they describe the person,
#: not a project. Stamped so Company User Permissions can filter them.
EMPLOYEE_SCOPED_DOCTYPES: dict[str, str] = {
	"Work Hours Summary": "personnel",
	"Contract Documents": "personnel",
}


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def get_project_company(project: str | None) -> str | None:
	"""Company that owns `project`, or None when the project is unset/missing."""
	if not project:
		return None
	return frappe.db.get_value("Project", project, "company")


def get_company_abbr(company: str | None) -> str | None:
	if not company:
		return None
	return frappe.db.get_value("Company", company, "abbr")


def resolve_project(doc) -> str | None:
	"""Name of the Project that owns `doc`, following an indirect hop if needed."""
	scope = PROJECT_SCOPED_DOCTYPES.get(doc.doctype)
	if not scope:
		return None

	if not scope.via:
		return doc.get(scope.project_field)

	link_field, link_doctype = scope.via
	parent = doc.get(link_field)
	if not parent:
		return None
	return frappe.db.get_value(link_doctype, parent, scope.project_field)


def resolve_company(doc) -> str | None:
	"""Entity that owns `doc`, derived from its Project."""
	return get_project_company(resolve_project(doc))


def active_project_scopes() -> dict[str, ProjectScope]:
	"""Registry entries whose DocType is actually installed on this site."""
	return {
		doctype: scope
		for doctype, scope in PROJECT_SCOPED_DOCTYPES.items()
		if frappe.db.exists("DocType", doctype)
	}


def describe_company(company: str | None) -> dict:
	"""Company plus what a form needs to name it and warn about it."""
	if not company:
		return {}

	label, currency = frappe.db.get_value(
		"Company", company, ["custom_display_name", "default_currency"]
	) or (None, None)
	return {"company": company, "label": label or company, "currency": currency}


def get_permitted_companies(user: str | None = None) -> list[str] | None:
	"""Entities a user is confined to, or None when they are unrestricted.

	Frappe's rule: no Company User Permission means every entity. Reports run raw
	SQL, which the permission layer never sees, so they have to ask for this and
	narrow their own rows.
	"""
	from frappe.permissions import get_user_permissions

	user = user or frappe.session.user
	if user == "Administrator":
		return None

	permitted = [
		row.get("doc") for row in (get_user_permissions(user).get("Company") or []) if row.get("doc")
	]
	return permitted or None


def get_home_company(user: str | None = None) -> str | None:
	"""The entity a user belongs to, as opposed to one they are working for.

	Their Employee record is the honest answer; the user default is a fallback
	for people who have a login but no Employee record.
	"""
	user = user or frappe.session.user
	company = frappe.db.get_value("Employee", {"user_id": user}, "company")
	return company or frappe.defaults.get_user_default("company", user)


@frappe.whitelist()
def get_project_entity(project: str) -> dict:
	"""Entity behind a project, for the form to describe before the save."""
	if not project:
		return {}
	frappe.has_permission("Project", doc=project, throw=True)
	return describe_company(get_project_company(project))


@frappe.whitelist()
def get_project_lock(project: str) -> dict:
	"""How many documents pin a project to its entity.

	One round trip rather than a count per DocType: the Project form asks on
	every load and only needs the total. `guard_project_company` does the
	per-DocType breakdown, which it needs to explain a refusal.
	"""
	if not project:
		return {"locked": False, "count": 0}
	frappe.has_permission("Project", doc=project, throw=True)

	scopes = [(dt, s) for dt, s in active_project_scopes().items() if not s.via]
	if not scopes:
		return {"locked": False, "count": 0}

	# Cancelled documents do not hold the entity: the refusal tells people to
	# remove or cancel dependants, so cancelling has to actually release it.
	union = " UNION ALL ".join(
		f"SELECT COUNT(*) AS c FROM `tab{doctype}` WHERE `{scope.project_field}` = %s AND docstatus != 2"
		for doctype, scope in scopes
	)
	total = frappe.db.sql(f"SELECT SUM(c) FROM ({union}) counts", [project] * len(scopes))[0][0]
	total = int(total or 0)
	return {"locked": bool(total), "count": total}


@frappe.whitelist()
def get_company_entity(company: str) -> dict:
	"""Describe an entity the form already knows the name of."""
	if not company:
		return {}
	frappe.has_permission("Company", doc=company, throw=True)
	return describe_company(company)


# ---------------------------------------------------------------------------
# Enforcement — wired to `validate` for every DocType in the registries
# ---------------------------------------------------------------------------


def apply_entity_scope(doc, method=None):
	"""`validate` dispatcher, wired once for every DocType in hooks.py.

	The registries above are the single source of truth for what is scoped, so a
	DocType is enforced the moment it is added to one — there is no second list
	in hooks.py to keep in step.
	"""
	if doc.doctype == "Project":
		guard_project_company(doc)
	elif doc.doctype in PROJECT_SCOPED_DOCTYPES:
		apply_project_scope(doc)
	elif doc.doctype in EMPLOYEE_SCOPED_DOCTYPES:
		apply_employee_scope(doc)


def apply_project_scope(doc, method=None):
	"""Stamp the owning entity onto a project-linked document and hold it there."""
	scope = PROJECT_SCOPED_DOCTYPES.get(doc.doctype)
	if not scope:
		return

	company = resolve_company(doc)
	if not company:
		# No project yet: nothing to inherit. The document's own company (if any)
		# is left alone so ERPNext defaults keep working.
		return

	_stamp_company(doc, scope.company_field, company)
	_reject_foreign_rows(doc, scope, company)


def apply_employee_scope(doc, method=None):
	"""Stamp the employing entity onto a personnel-owned document."""
	employee_field = EMPLOYEE_SCOPED_DOCTYPES.get(doc.doctype)
	if not employee_field:
		return

	employee = doc.get(employee_field)
	if not employee:
		return

	company = frappe.db.get_value("Employee", employee, "company")
	if company:
		_stamp_company(doc, "company", company)


def _stamp_company(doc, fieldname: str, company: str) -> None:
	current = doc.get(fieldname)
	if current == company:
		return

	if not current or doc.docstatus == 0:
		doc.set(fieldname, company)
		return

	# Submitted documents are already in the ledger under `current`. Moving them
	# to another entity silently would rewrite history, so refuse instead.
	frappe.throw(
		_(
			"This document is submitted under {0}, but it now points at work owned by {1}."
			"<br>Cancel and amend it to move it to another entity."
		).format(frappe.bold(current), frappe.bold(company)),
		title=_("Entity Locked"),
	)


def _reject_foreign_rows(doc, scope: ProjectScope, company: str) -> None:
	"""A single document may not span entities via its child rows."""
	for table_field, project_field in scope.child_project_fields:
		for row in doc.get(table_field) or []:
			row_project = row.get(project_field)
			if not row_project:
				continue

			row_company = get_project_company(row_project)
			if row_company and row_company != company:
				frappe.throw(
					_(
						"Row {0}: project {1} belongs to {2}, but this document belongs to {3}."
						"<br>A single document cannot cover more than one entity."
					).format(
						row.idx,
						frappe.bold(row_project),
						frappe.bold(row_company),
						frappe.bold(company),
					),
					title=_("Mixed Entities"),
				)


# ---------------------------------------------------------------------------
# Project — the company is locked once the project has documents under it
# ---------------------------------------------------------------------------


def guard_project_company(doc, method=None):
	"""Block a Project's company change once documents exist under it."""
	if doc.is_new():
		return

	previous = doc.get_doc_before_save()
	if not previous or previous.company == doc.company:
		return

	dependents = count_project_documents(doc.name)
	if not dependents:
		return

	listed = "<br>".join(f"{count} &times; {doctype}" for doctype, count in dependents.items())
	frappe.throw(
		_(
			"This project already owns documents under {0}, so its entity can no longer change:"
			"<br>{1}<br>Remove or cancel them first."
		).format(frappe.bold(previous.company), listed),
		title=_("Entity Locked"),
	)


def count_project_documents(project: str) -> dict[str, int]:
	"""How many documents of each DocType hang off `project`."""
	counts: dict[str, int] = {}
	for doctype, scope in active_project_scopes().items():
		if scope.via:
			# Reached through its parent, which is counted in its own right.
			continue
		count = frappe.db.count(doctype, {scope.project_field: project, "docstatus": ("!=", 2)})
		if count:
			counts[doctype] = count
	return counts


# ---------------------------------------------------------------------------
# Naming — each entity gets its own counter
# ---------------------------------------------------------------------------


def entity_abbr(doc) -> str | None:
	"""Abbreviation of the entity owning `doc`, or None when it cannot be resolved.

	Naming runs before `validate`, so the company field is usually still empty at
	this point and the entity has to come from the project.
	"""
	scope = PROJECT_SCOPED_DOCTYPES.get(doc.doctype)
	company = doc.get(scope.company_field) if scope else None
	return get_company_abbr(company or resolve_company(doc))


def entity_series_name(doc, series: str) -> str | None:
	"""`<ABBR>-<series>` counter name, or None when the entity is unknown.

	Returning None leaves `doc.name` unset so Frappe falls back to the DocType's
	own `autoname` — a document saved before its project is known still gets a
	valid name.
	"""
	abbr = entity_abbr(doc)
	if not abbr:
		return None
	return make_autoname(f"{abbr}-{series}", doc=doc)
