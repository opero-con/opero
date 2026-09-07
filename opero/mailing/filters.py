"""Permission-aware Contact filtering and exports using membership statuses."""

from collections import defaultdict
from contextlib import contextmanager

import frappe
from frappe import _

from opero.mailing.membership import CHILD, FIELD


def selection(value):
	value = frappe.parse_json(value) or {}
	groups = value.get("mailing_lists") or []
	mode, state = value.get("match", "Any"), value.get("status", "")
	if (
		not isinstance(groups, list)
		or mode not in ("Any", "All")
		or state not in ("", "Pending", "Confirmed", "Unsubscribed", "No email")
	):
		frappe.throw(_("Invalid Mailing List filters."))
	return groups, mode, state


def matching_names(value):
	groups, mode, state = selection(value)
	filters = {"parenttype": "Contact", "parentfield": FIELD}
	if groups:
		filters["mailing_list"] = ["in", groups]
	if state:
		filters["subscription_status"] = state
	if not groups and not state:
		return None
	matches = defaultdict(set)
	for row in frappe.get_all(CHILD, filters=filters, fields=["parent", "mailing_list"]):
		matches[row.parent].add(row.mailing_list)
	return [name for name, lists in matches.items() if mode == "Any" or not groups or set(groups) <= lists]


@contextmanager
def list_filter():
	value = frappe.form_dict.pop("opero_mailing_filter", None)
	old = frappe.form_dict.get("filters")
	try:
		if value and frappe.form_dict.get("doctype") == "Contact":
			names = matching_names(value)
			if names is not None:
				filters = frappe.parse_json(old) or []
				if isinstance(filters, dict):
					filters = [["Contact", k, "=", v] for k, v in filters.items()]
				frappe.form_dict.filters = [*filters, ["Contact", "name", "in", names or [""]]]
		yield
	finally:
		if old is None:
			frappe.form_dict.pop("filters", None)
		else:
			frappe.form_dict.filters = old
		if value is not None:
			frappe.form_dict.opero_mailing_filter = value


@frappe.whitelist()
def get():
	from frappe.desk.reportview import get as native_get

	with list_filter():
		return native_get()


@frappe.whitelist()
def get_count():
	from frappe.desk.reportview import get_count as native_count

	with list_filter():
		return native_count()


def export_rows(filters=None, or_filters=None, mailing_filter=None):
	frappe.has_permission("Contact", "export", throw=True)
	filters = frappe.parse_json(filters) or []
	names = matching_names(mailing_filter)
	if names is not None:
		filters = [*filters, ["Contact", "name", "in", names or [""]]]
	contacts = frappe.get_list(
		"Contact",
		filters=filters,
		or_filters=frappe.parse_json(or_filters) or [],
		fields=["name", "full_name", "email_id", "company_name", "phone", "mobile_no"],
		limit_page_length=0,
		order_by="full_name",
	)
	groups, _, _ = selection(mailing_filter)
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
	if groups:
		child_filters["mailing_list"] = ["in", groups]
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
def export_contacts(filters=None, or_filters=None, mailing_filter=None):
	from frappe.core.doctype.access_log.access_log import make_access_log
	from frappe.utils.csvutils import build_csv_response

	rows = export_rows(filters, or_filters, mailing_filter)
	make_access_log(doctype="Contact", file_type="CSV", method="Export", filters=filters)
	build_csv_response(rows, "Contacts with Mailing Lists")
