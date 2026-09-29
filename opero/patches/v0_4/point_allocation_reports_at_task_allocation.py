"""Point the saved allocation reports at Task Allocation.

`import_fc_site_config` only upserts once, so the rewritten queries in
`data/fc_site_config/report.json` do not reach sites where it has already run.
"""

import json

import frappe

from opero.patches.v0_2.import_fc_site_config import DATA_DIR, _upsert

LEGACY_TABLES = ("tabTask Time Distribution", "tabTask Time Allocation")


def execute():
	reports = json.loads((DATA_DIR / "report.json").read_text())
	for report in reports:
		if report.get("ref_doctype") == "Task Allocation" or "`tabTask Allocation`" in (
			report.get("query") or ""
		):
			_upsert(report)

	stale = frappe.get_all(
		"Report",
		or_filters=[["query", "like", f"%{table}%"] for table in LEGACY_TABLES]
		+ [["ref_doctype", "=", "Task Time Distribution"]],
		pluck="name",
	)
	if stale:
		frappe.throw(f"Reports still read the old allocation tables: {', '.join(stale)}")
