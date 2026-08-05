"""Sprout each Project's existing company onto every document beneath it.

Projects keep whatever company they already have — nothing is reassigned. This
only fills in the company that was previously implicit on their child documents,
so entity filters and Company User Permissions have something to work with.

Written as set-based UPDATEs: the volumes are large, `modified` should not move
for a backfill, and submitted documents have to be stamped too.
"""

from __future__ import annotations

import frappe

from opero import entity


def execute():
	scopes = entity.active_project_scopes()

	# Documents that reach their Project through another document (Actual Spend via
	# Cash Advance, Activity Cost via Activity Type) read the company off that
	# parent, so the parent has to be stamped first.
	ordered = sorted(scopes.items(), key=lambda item: bool(item[1].via))

	for doctype, scope in ordered:
		if not _has_column(doctype, scope.company_field):
			continue

		if scope.via:
			link_field, link_doctype = scope.via
			if not _has_column(link_doctype, scope.company_field):
				continue
			updated = _backfill_via_parent(doctype, scope, link_field, link_doctype)
		else:
			updated = _backfill_from_project(doctype, scope)

		if updated:
			print(f"Opero: stamped company on {updated} {doctype} document(s)")

	for doctype, employee_field in entity.EMPLOYEE_SCOPED_DOCTYPES.items():
		if not (frappe.db.exists("DocType", doctype) and _has_column(doctype, "company")):
			continue
		updated = _backfill_from_employee(doctype, employee_field)
		if updated:
			print(f"Opero: stamped company on {updated} {doctype} document(s)")

	frappe.db.commit()


def _has_column(doctype: str, fieldname: str) -> bool:
	return fieldname in frappe.db.get_table_columns(doctype)


def _backfill_from_project(doctype: str, scope: entity.ProjectScope) -> int:
	return _run(
		f"""
		UPDATE `tab{doctype}` doc
		JOIN `tabProject` project ON project.name = doc.`{scope.project_field}`
		SET doc.`{scope.company_field}` = project.company
		WHERE project.company IS NOT NULL
		  AND project.company != ''
		  AND (doc.`{scope.company_field}` IS NULL
		       OR doc.`{scope.company_field}` != project.company)
		"""
	)


def _backfill_via_parent(doctype: str, scope: entity.ProjectScope, link_field: str, link_doctype: str) -> int:
	return _run(
		f"""
		UPDATE `tab{doctype}` doc
		JOIN `tab{link_doctype}` parent ON parent.name = doc.`{link_field}`
		SET doc.`{scope.company_field}` = parent.`{scope.company_field}`
		WHERE parent.`{scope.company_field}` IS NOT NULL
		  AND parent.`{scope.company_field}` != ''
		  AND (doc.`{scope.company_field}` IS NULL
		       OR doc.`{scope.company_field}` != parent.`{scope.company_field}`)
		"""
	)


def _backfill_from_employee(doctype: str, employee_field: str) -> int:
	return _run(
		f"""
		UPDATE `tab{doctype}` doc
		JOIN `tabEmployee` employee ON employee.name = doc.`{employee_field}`
		SET doc.company = employee.company
		WHERE employee.company IS NOT NULL
		  AND employee.company != ''
		  AND (doc.company IS NULL OR doc.company != employee.company)
		"""
	)


def _run(query: str) -> int:
	frappe.db.sql(query)
	return frappe.db.sql("SELECT ROW_COUNT()")[0][0] or 0
