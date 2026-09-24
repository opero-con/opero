"""Permission-aware Contact exports with mailing-list membership statuses."""

from collections import defaultdict

import frappe

from opero.mailing.membership import CHILD, FIELD


def export_rows(filters=None, or_filters=None):
	frappe.has_permission("Contact", "export", throw=True)
	filters = frappe.parse_json(filters) or []
	contacts = frappe.get_list(
		"Contact",
		filters=filters,
		or_filters=frappe.parse_json(or_filters) or [],
		fields=["name", "full_name", "email_id", "company_name", "phone", "mobile_no"],
		limit_page_length=0,
		order_by="full_name",
	)
	rows = [
		[
			"Contact",
			"Full Name",
			"Primary Email",
			"Company",
			"Phone",
			"Mobile",
			"Mailing List",
			"Membership Status",
		]
	]
	if not contacts:
		return rows
	by_contact = defaultdict(list)
	child_filters = {
		"parent": ["in", [c.name for c in contacts]],
		"parenttype": "Contact",
		"parentfield": FIELD,
	}
	for row in frappe.get_all(
		CHILD,
		filters=child_filters,
		fields=["parent", "mailing_list", "subscription_status"],
		order_by="mailing_list",
	):
		by_contact[row.parent].append(row)
	for contact in contacts:
		base = [
			contact.get(k) for k in ("name", "full_name", "email_id", "company_name", "phone", "mobile_no")
		]
		for row in by_contact[contact.name] or [frappe._dict()]:
			rows.append([*base, row.mailing_list or "", row.subscription_status or ""])
	return rows


@frappe.whitelist()
def export_contacts(filters=None, or_filters=None):
	from frappe.core.doctype.access_log.access_log import make_access_log
	from frappe.utils.csvutils import build_csv_response

	rows = export_rows(filters, or_filters)
	make_access_log(doctype="Contact", file_type="CSV", method="Export", filters=filters)
	build_csv_response(rows, "Contacts with Mailing Lists")
