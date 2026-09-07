"""Ship Timesheet Customize Form changes for export-friendly layout.

- Keep Employee Name unhidden in meta so Report/List export can include it;
  the form hides it again via `timesheet.js` (`toggle_display`).
- Hide Start Date / End Date on the form (still on the DocType).
- Clear the Employee Detail section label and stop making it collapsible.
- Reorder fields so Project / Company / PM sit with the contributor block.

`import_fc_site_config` only upserts, so edits in
`data/fc_site_config/property_setter.json` do not reach sites where it has
already run. This does. Deleting a setter also needs an explicit patch.
"""

from __future__ import annotations

import json

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

FIELD_ORDER = [
	"workflow_state",
	"custom_section_break_zm48z",
	"currency",
	"custom_column_break_mopvs",
	"exchange_rate",
	"custom_column_break_nk7tx",
	"custom_column_break_rnmhl",
	"employee_detail",
	"employee",
	"employee_name",
	"column_break_9",
	"parent_project",
	"custom_total_spent_hours",
	"department",
	"user",
	"custom_column_break_w8osb",
	"custom_allocated_hours",
	"company",
	"custom_pm_name",
	"custom_section_break_ke6yk",
	"title",
	"naming_series",
	"customer",
	"sales_invoice",
	"custom_column_break_u3jje",
	"custom_pb_rate",
	"custom_project_name",
	"custom_pm_notified",
	"column_break_3",
	"status",
	"custom_project_manager",
	"custom_pm_email",
	"section_break_18",
	"note",
	"amended_from",
	"section_break_5",
	"time_logs",
	"working_hours",
	"custom_column_break_kqerb",
	"start_date",
	"custom_column_break_hyquf",
	"end_date",
	"custom_column_break_mjuix",
	"total_hours",
	"billing_details",
	"total_billable_hours",
	"base_total_billable_amount",
	"base_total_billed_amount",
	"base_total_costing_amount",
	"column_break_10",
	"total_billed_hours",
	"total_billable_amount",
	"total_billed_amount",
	"total_costing_amount",
	"per_billed",
]


def execute():
	if not frappe.db.exists("DocType", "Timesheet"):
		return

	_set_property("employee_name", "hidden", "0", "Check")
	_set_property("start_date", "hidden", "1", "Check")
	_set_property("end_date", "hidden", "1", "Check")
	_set_property("employee_detail", "label", "", "Data")
	_delete_property("Timesheet-employee_detail-collapsible")
	_set_field_order(FIELD_ORDER)
	frappe.clear_cache(doctype="Timesheet")


def _set_property(fieldname: str, property_name: str, value: str, property_type: str) -> None:
	name = f"Timesheet-{fieldname}-{property_name}"
	if frappe.db.exists("Property Setter", name):
		frappe.db.set_value("Property Setter", name, "value", value)
		return

	make_property_setter(
		"Timesheet",
		fieldname,
		property_name,
		value,
		property_type,
		validate_fields_for_doctype=False,
	)


def _delete_property(name: str) -> None:
	if frappe.db.exists("Property Setter", name):
		frappe.delete_doc("Property Setter", name, ignore_permissions=True, force=True)


def _set_field_order(order: list[str]) -> None:
	name = "Timesheet-main-field_order"
	value = json.dumps(order)
	if frappe.db.exists("Property Setter", name):
		frappe.db.set_value("Property Setter", name, "value", value)
		return

	make_property_setter(
		"Timesheet",
		None,
		"field_order",
		value,
		"Data",
		for_doctype=True,
		validate_fields_for_doctype=False,
	)
	created = frappe.db.get_value(
		"Property Setter",
		{"doc_type": "Timesheet", "property": "field_order"},
		"name",
	)
	if created and created != name:
		frappe.rename_doc("Property Setter", created, name, force=True)
