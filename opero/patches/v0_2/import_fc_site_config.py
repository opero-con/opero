"""Import FC site-config documents, skipping rows whose DocTypes are not installed.

Stored under opero/data/fc_site_config (not fixtures/) so sites without HRMS
do not fail the whole migrate when Leave Application / Travel Request are missing.
"""

from __future__ import annotations

import json
from pathlib import Path

import frappe


DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "fc_site_config"

# Load order matters for Workflow dependencies.
FILES = [
	"workflow_action_master.json",
	"workflow_state.json",
	"custom_field.json",
	"property_setter.json",
	"print_format.json",
	"notification.json",
	"report.json",
	"workflows.json",
]


def _doctype_for_doc(doc: dict) -> str | None:
	dt = doc.get("doctype")
	if dt == "Custom Field":
		return doc.get("dt")
	if dt == "Property Setter":
		return doc.get("doc_type")
	if dt == "Print Format":
		return doc.get("doc_type")
	if dt == "Notification":
		return doc.get("document_type")
	if dt == "Report":
		return doc.get("ref_doctype")
	if dt == "Workflow":
		return doc.get("document_type")
	return None


def _upsert(doc: dict) -> str:
	doctype = doc.get("doctype")
	name = doc.get("name")
	if not doctype or not name:
		return "skip"

	# Drop broken optional links that often don't exist on every site.
	if doctype == "Report" and doc.get("letter_head"):
		if not frappe.db.exists("Letter Head", doc["letter_head"]):
			doc["letter_head"] = None

	if frappe.db.exists(doctype, name):
		existing = frappe.get_doc(doctype, name)
		existing.update(doc)
		existing.flags.ignore_permissions = True
		existing.flags.ignore_mandatory = True
		existing.flags.ignore_links = True
		existing.flags.ignore_validate = True
		existing.save()
		return "updated"

	new_doc = frappe.get_doc(doc)
	new_doc.flags.ignore_permissions = True
	new_doc.flags.ignore_mandatory = True
	new_doc.flags.ignore_links = True
	new_doc.flags.ignore_validate = True
	new_doc.insert()
	return "inserted"


def execute():
	if not DATA_DIR.is_dir():
		return

	stats = {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0}

	for fname in FILES:
		path = DATA_DIR / fname
		if not path.exists():
			continue
		docs = json.loads(path.read_text())
		if not isinstance(docs, list):
			continue

		for doc in docs:
			ref_dt = _doctype_for_doc(doc)
			# Masters without a linked form DocType
			if doc.get("doctype") in ("Workflow State", "Workflow Action Master"):
				ref_dt = None
			if ref_dt and not frappe.db.exists("DocType", ref_dt):
				stats["skipped"] += 1
				continue
			try:
				result = _upsert(doc)
				if result in stats:
					stats[result] += 1
			except Exception:
				stats["errors"] += 1
				frappe.log_error(
					frappe.get_traceback(),
					f"FC site-config import failed: {doc.get('doctype')} {doc.get('name')}",
				)

	frappe.logger("opero").info(f"import_fc_site_config: {stats}")
