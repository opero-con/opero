from __future__ import annotations

import erpnext
import frappe

from opero.opero_site.utils import slugify


TEST_EMAIL_PREFIX = "website-test-"


def clear_website_test_employees() -> None:
	frappe.db.delete("Employee", {"company_email": ["like", f"{TEST_EMAIL_PREFIX}%"]})


def make_website_employee(display_name: str, **fields):
	payload = {
		"doctype": "Employee",
		"first_name": display_name,
		"company_email": f"{TEST_EMAIL_PREFIX}{slugify(display_name)}@example.com",
		"gender": frappe.db.get_value("Gender", {}, "name"),
		"date_of_birth": "1990-01-01",
		"date_of_joining": "2020-01-01",
		"status": "Active",
		"company": erpnext.get_default_company(),
		"role": "Water Specialist",
		"show_on_website": 1,
		"sort_order": 10,
	}
	payload.update(fields)
	return frappe.get_doc(payload).insert(ignore_permissions=True)
