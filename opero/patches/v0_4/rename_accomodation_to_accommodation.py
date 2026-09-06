"""Spell Accommodation correctly on the Travel Request child table."""

from __future__ import annotations

import frappe
from frappe.model.utils.rename_field import rename_field

OLD = "Accomodation"
NEW = "Accommodation"


def execute():
	if frappe.db.exists("DocType", OLD):
		# sync_all may already have imported the correctly spelled DocType empty.
		if frappe.db.exists("DocType", NEW):
			frappe.delete_doc("DocType", NEW, force=True, ignore_permissions=True)
		if frappe.db.table_exists(NEW) and frappe.db.table_exists(OLD):
			frappe.db.sql_ddl(f"DROP TABLE `tab{NEW}`")
		frappe.rename_doc("DocType", OLD, NEW, force=True)
	elif frappe.db.table_exists(OLD) and frappe.db.exists("DocType", NEW):
		# Failed mid-rename can leave the misspelled table behind.
		frappe.db.sql_ddl(f"DROP TABLE `tab{OLD}`")

	frappe.reload_doc("opero", "doctype", "accommodation", force=True)

	if frappe.db.exists("DocType", NEW) and frappe.db.has_column(NEW, "accomodation_type"):
		rename_field(NEW, "accomodation_type", "accommodation_type")

	_fix_travel_request_custom_fields()
	_rewrite_property_setters()
	_rewrite_print_formats()


def _fix_travel_request_custom_fields() -> None:
	_update_custom_field(
		old_fieldname="custom_accomodation",
		new_fieldname="custom_accommodation",
		label="Accommodation",
	)
	_update_custom_field(
		old_fieldname="custom_accomodation_details",
		new_fieldname="custom_accommodation_details",
		label="Accommodation Details",
		options=NEW,
	)
	if frappe.db.table_exists(NEW):
		frappe.db.sql(
			f"""
			UPDATE `tab{NEW}`
			SET parentfield = 'custom_accommodation_details'
			WHERE parentfield = 'custom_accomodation_details'
			"""
		)


def _update_custom_field(
	*,
	old_fieldname: str,
	new_fieldname: str,
	label: str,
	options: str | None = None,
) -> None:
	name = frappe.db.get_value("Custom Field", {"dt": "Travel Request", "fieldname": old_fieldname}, "name")
	if not name:
		name = frappe.db.get_value("Custom Field", {"dt": "Travel Request", "fieldname": new_fieldname}, "name")
	if not name:
		return

	doc = frappe.get_doc("Custom Field", name)
	if doc.fieldname == old_fieldname and old_fieldname != new_fieldname:
		if frappe.db.has_column("Travel Request", old_fieldname):
			frappe.db.rename_column("Travel Request", old_fieldname, new_fieldname)
		doc.db_set("fieldname", new_fieldname, update_modified=False)
		frappe.db.set_value(
			"Custom Field",
			{"insert_after": old_fieldname, "dt": "Travel Request"},
			"insert_after",
			new_fieldname,
			update_modified=False,
		)

	doc.db_set("label", label, update_modified=False)
	if options is not None:
		doc.db_set("options", options, update_modified=False)


def _rewrite_property_setters() -> None:
	replacements = (
		("custom_accomodation_details", "custom_accommodation_details"),
		("custom_accomodation", "custom_accommodation"),
		(OLD, NEW),
	)
	for row in frappe.get_all(
		"Property Setter",
		filters={"doc_type": "Travel Request"},
		fields=["name", "value"],
	):
		value = row.value
		if not value:
			continue
		updated = value
		for old, new in replacements:
			updated = updated.replace(old, new)
		if updated != value:
			frappe.db.set_value("Property Setter", row.name, "value", updated, update_modified=False)


def _rewrite_print_formats() -> None:
	replacements = (
		("custom_accomodation_details", "custom_accommodation_details"),
		("custom_accomodation", "custom_accommodation"),
		("Accomodation Type", "Accommodation Type"),
		("Accomodation Details", "Accommodation Details"),
		(OLD, NEW),
	)
	for row in frappe.get_all(
		"Print Format",
		filters={"doc_type": "Travel Request"},
		fields=["name", "format_data"],
	):
		format_data = row.format_data
		if not format_data:
			continue
		updated = format_data
		for old, new in replacements:
			updated = updated.replace(old, new)
		if updated != format_data:
			frappe.db.set_value("Print Format", row.name, "format_data", updated, update_modified=False)
