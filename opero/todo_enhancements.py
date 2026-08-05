from __future__ import annotations

import re
from collections.abc import Iterable

import frappe
from frappe.model.document import Document
from frappe.permissions import AUTOMATIC_ROLES
from frappe.utils.data import now_datetime
from frappe.utils.data import strip_html
from frappe.utils.html_utils import unescape_html


USER_TOKEN_SPLIT = re.compile(r"[\n,;]+")


def validate_todo(doc: Document, _method: str | None = None):
	_autofill_title_from_reference(doc)
	_sync_title_and_description(doc)
	_sync_owner_display(doc)
	_sync_status_timestamps(doc)
	_validate_title_or_description(doc)
	_normalize_assignees(doc)


def on_update_todo(doc: Document, _method: str | None = None):
	_send_assignment_email(doc)


def get_permission_query_conditions(user=None):
	if not user:
		user = frappe.session.user

	todo_roles = frappe.permissions.get_doctype_roles("ToDo")
	todo_roles = set(todo_roles) - set(AUTOMATIC_ROLES)

	if any(role in todo_roles for role in frappe.get_roles(user)):
		return None

	escaped = frappe.db.escape(user)
	return (
		f"(`tabToDo`.allocated_to = {escaped}"
		f" OR `tabToDo`.assigned_by = {escaped}"
		f" OR EXISTS ("
		f"SELECT 1 FROM `tabToDo Assignee`"
		f" WHERE `tabToDo Assignee`.parent = `tabToDo`.name"
		f" AND `tabToDo Assignee`.user = {escaped}"
		f"))"
	)


def has_permission(doc: Document, ptype: str = "read", user: str | None = None) -> bool:
	user = user or frappe.session.user

	todo_roles = frappe.permissions.get_doctype_roles("ToDo", ptype)
	todo_roles = set(todo_roles) - set(AUTOMATIC_ROLES)

	if any(role in todo_roles for role in frappe.get_roles(user)):
		return True

	if doc.allocated_to == user or doc.assigned_by == user:
		return True

	assignees = [row.user for row in (getattr(doc, "custom_assignees", None) or []) if getattr(row, "user", None)]
	return user in assignees


def _autofill_title_from_reference(doc: Document):
	"""Ported from FC Server Script Custom_Title."""
	if (getattr(doc, "custom_title", None) or "").strip():
		return

	reference_type = getattr(doc, "reference_type", None)
	reference_name = getattr(doc, "reference_name", None)
	if reference_type and reference_name:
		try:
			ref_doc = frappe.get_doc(reference_type, reference_name)
			title = (
				getattr(ref_doc, "title", None)
				or getattr(ref_doc, "subject", None)
				or ref_doc.name
			)
			doc.custom_title = f"{reference_type}: {title}"
		except Exception:
			doc.custom_title = f"{reference_type}: {reference_name}"
		return

	doc.custom_title = getattr(doc, "description", None) or "General Task"


def _sync_title_and_description(doc: Document):
	raw_title = (getattr(doc, "custom_title", None) or "").strip()
	raw_description = (getattr(doc, "description", None) or "").strip()
	title = _extract_plain_text(raw_title)
	description = _extract_plain_text(raw_description)

	if raw_title and title != raw_title:
		doc.custom_title = title

	if description and not title:
		doc.custom_title = description


def _send_assignment_email(doc: Document):
	"""Ported from FC Server Script ToDo Email Notification."""
	if getattr(doc, "custom_email_sent", None):
		return
	if not getattr(doc, "allocated_to", None) or getattr(doc, "status", None) != "Open":
		return

	email = frappe.db.get_value("User", doc.allocated_to, "email")
	if not email:
		return

	todo_link = frappe.utils.get_url_to_form("ToDo", doc.name)
	message = (
		f"You've been assigned a ToDo: <b>{doc.custom_title or doc.name}</b><br><br>"
		f'<a href="{todo_link}">Open the ToDo</a>'
	)
	frappe.sendmail(
		recipients=email,
		subject="New ToDo Assigned",
		message=message,
		reference_doctype="ToDo",
		reference_name=doc.name,
	)
	frappe.db.set_value("ToDo", doc.name, "custom_email_sent", 1, update_modified=False)


def _extract_plain_text(value: str | None) -> str:
	if not value:
		return ""

	text = unescape_html(strip_html(value))
	return " ".join(text.split()).strip()


def _validate_title_or_description(doc: Document):
	title = _extract_plain_text(getattr(doc, "custom_title", None))
	description = _extract_plain_text(getattr(doc, "description", None))

	if not title and not description:
		frappe.throw("Add either Title or Description before saving this ToDo.")


def _sync_owner_display(doc: Document):
	owner = (getattr(doc, "owner", None) or "").strip()
	if owner and getattr(doc, "custom_created_by", None) != owner:
		doc.custom_created_by = owner


def _sync_status_timestamps(doc: Document):
	status = (getattr(doc, "status", None) or "").strip()
	current_closed_on = getattr(doc, "custom_closed_on", None)
	current_cancelled_on = getattr(doc, "custom_cancelled_on", None)

	if status == "Closed":
		if not current_closed_on:
			doc.custom_closed_on = now_datetime()
		if current_cancelled_on:
			doc.custom_cancelled_on = None
		return

	if status == "Cancelled":
		if not current_cancelled_on:
			doc.custom_cancelled_on = now_datetime()
		if current_closed_on:
			doc.custom_closed_on = None
		return

	if current_closed_on:
		doc.custom_closed_on = None

	if current_cancelled_on:
		doc.custom_cancelled_on = None


def _normalize_assignees(doc: Document):
	valid_assignees = _validate_assignees_exist(_get_doc_assignees(doc))
	primary = valid_assignees[0] if valid_assignees else ""
	_set_doc_assignees(doc, valid_assignees)
	doc.allocated_to = primary or None


def _parse_assignees(raw_values) -> list[str]:
	if not raw_values:
		return []

	if isinstance(raw_values, str):
		return _dedupe([token.strip() for token in USER_TOKEN_SPLIT.split(raw_values) if token.strip()])

	if isinstance(raw_values, list):
		users = []
		for row in raw_values:
			user = ""
			if isinstance(row, str):
				user = row.strip()
			elif isinstance(row, dict):
				user = (row.get("user") or "").strip()
			else:
				user = (getattr(row, "user", None) or "").strip()

			if user:
				users.append(user)

		return _dedupe(users)

	return []


def _get_doc_assignees(doc: Document) -> list[str]:
	return _parse_assignees(getattr(doc, "custom_assignees", None))


def _set_doc_assignees(doc: Document, users: list[str]):
	field_meta = doc.meta.get_field("custom_assignees") if getattr(doc, "meta", None) else None
	if field_meta and field_meta.fieldtype == "Table MultiSelect":
		doc.set("custom_assignees", [{"user": user} for user in users])
		return

	current_value = getattr(doc, "custom_assignees", None)
	if isinstance(current_value, list):
		doc.set("custom_assignees", [{"user": user} for user in users])
	else:
		doc.custom_assignees = "\n".join(users)


def _validate_assignees_exist(users: Iterable[str]) -> list[str]:
	users = [user for user in users if user]
	if not users:
		return []

	existing_users = set(
		frappe.get_all(
			"User",
			filters={"name": ("in", users), "enabled": 1},
			pluck="name",
		)
	)
	invalid_users = [user for user in users if user not in existing_users]
	if invalid_users:
		frappe.throw(
			"Unknown or disabled user(s): {0}. Use valid existing user IDs from this site.".format(
				", ".join(invalid_users)
			)
		)

	return [user for user in users if user in existing_users]


def _dedupe(users: list[str]) -> list[str]:
	seen: set[str] = set()
	result: list[str] = []
	for user in users:
		if user in seen:
			continue
		seen.add(user)
		result.append(user)

	return result
