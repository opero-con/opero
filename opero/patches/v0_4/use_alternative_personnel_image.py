"""Use Employee Image by default, retaining the existing portrait as an alternative."""

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from opero.opero_site.load import adopt_imported_portrait


def execute():
	already_migrated = frappe.db.exists("Custom Field", "Employee-use_alternative_image")
	order = [field.fieldname for field in frappe.get_meta("Employee").fields]
	create_custom_fields({"Employee": [
		{"fieldname": "use_alternative_image", "fieldtype": "Check",
		 "label": "Use alternative image", "default": "0", "insert_after": "website_portrait_section"},
		{"fieldname": "portrait", "fieldtype": "Attach Image", "label": "Alternative image",
		 "depends_on": "eval:doc.use_alternative_image", "insert_after": "use_alternative_image"},
	]}, update=True)
	if not already_migrated:
		for name in frappe.get_all("Employee", pluck="name"):
			doc = frappe.get_doc("Employee", name)
			use_alternative = bool(doc.get("portrait")) and not bool(doc.get("use_employee_image"))
			if adopt_imported_portrait(doc):
				frappe.db.set_value("Employee", name, "image", doc.image, update_modified=False)
				use_alternative = False
			frappe.db.set_value("Employee", name, "use_alternative_image", int(use_alternative), update_modified=False)
	if "use_employee_image" in order:
		order = ["use_alternative_image" if field == "use_employee_image" else field for field in order]
		if len(order) != len(set(order)):
			order = list(dict.fromkeys(order))
		make_property_setter("Employee", None, "field_order", json.dumps(order), "Data",
			for_doctype=True, validate_fields_for_doctype=False)
	if frappe.db.exists("Custom Field", "Employee-use_employee_image"):
		frappe.delete_doc("Custom Field", "Employee-use_employee_image", ignore_permissions=True)
	frappe.db.set_value("DocType", "Employee", "modified", frappe.utils.now())
	frappe.clear_cache(doctype="Employee")
