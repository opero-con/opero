from __future__ import annotations

import re
from collections.abc import Iterable

import frappe
from frappe.model.document import Document
from frappe.utils import cint
from frappe.utils.data import strip_html
from frappe.utils.html_utils import unescape_html


USER_TOKEN_SPLIT = re.compile(r"[\n,;]+")
SYNC_FIELDS = (
	"description",
	"custom_title",
	"priority",
	"date",
	"reference_type",
	"reference_name",
)


def validate_todo(doc: Document, _method: str | None = None):
	_sync_title_and_description(doc)
	_sync_owner_display(doc)
	_validate_title_or_description(doc)
	_normalize_assignees(doc)


def sync_child_todos(doc: Document, _method: str | None = None):
	if _should_skip_sync(doc):
		return

	group_id = _ensure_assignment_group(doc)
	desired_secondary_assignees = _get_desired_secondary_assignees(doc)
	existing_children = frappe.get_all(
		"ToDo",
		filters={"custom_parent_todo": doc.name},
		fields=["name", "allocated_to"],
	)
	existing_children_by_user = {row.allocated_to: row for row in existing_children if row.allocated_to}

	for user in desired_secondary_assignees:
		existing_child = existing_children_by_user.get(user)
		if existing_child:
			_sync_child_values(existing_child.name, doc, group_id)
		else:
			_create_child_todo(doc, user, group_id)

	desired_set = set(desired_secondary_assignees)
	for child in existing_children:
		if child.allocated_to not in desired_set:
			frappe.delete_doc("ToDo", child.name, ignore_permissions=True, force=True)


def delete_child_todos(doc: Document, _method: str | None = None):
	if _should_skip_sync(doc):
		return

	for child_name in frappe.get_all("ToDo", filters={"custom_parent_todo": doc.name}, pluck="name"):
		frappe.delete_doc("ToDo", child_name, ignore_permissions=True, force=True)


def _should_skip_sync(doc: Document) -> bool:
	return bool(getattr(doc.flags, "opero_skip_sync", False) or cint(getattr(doc, "custom_is_group_child", 0)))


def _sync_title_and_description(doc: Document):
	raw_title = (getattr(doc, "custom_title", None) or "").strip()
	raw_description = (getattr(doc, "description", None) or "").strip()
	title = _extract_plain_text(raw_title)
	description = _extract_plain_text(raw_description)

	if raw_title and title != raw_title:
		doc.custom_title = title

	if description and not title:
		doc.custom_title = description


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


def _normalize_assignees(doc: Document):
	assignees = _get_doc_assignees(doc)

	if not assignees:
		legacy_primary = (getattr(doc, "allocated_to", None) or "").strip()
		legacy_additional = _parse_assignees(getattr(doc, "custom_additional_assignees", None))
		assignees = [user for user in [legacy_primary, *legacy_additional] if user]

	valid_assignees = _validate_assignees_exist(assignees)
	primary = valid_assignees[0] if valid_assignees else ""
	additional = valid_assignees[1:] if len(valid_assignees) > 1 else []

	_set_doc_assignees(doc, valid_assignees)
	doc.allocated_to = primary or None
	doc.custom_additional_assignees = "\n".join(additional)


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


def _ensure_assignment_group(doc: Document) -> str:
	group_id = (getattr(doc, "custom_assignment_group", None) or "").strip() or doc.name
	if not group_id:
		return ""

	if getattr(doc, "custom_assignment_group", None) != group_id:
		doc.custom_assignment_group = group_id
		frappe.db.set_value("ToDo", doc.name, "custom_assignment_group", group_id, update_modified=False)

	return group_id


def _get_desired_secondary_assignees(doc: Document) -> list[str]:
	assignees = _get_doc_assignees(doc)
	if not assignees:
		return []

	primary = assignees[0]
	return [user for user in assignees[1:] if user and user != primary]


def _sync_child_values(child_name: str, parent_doc: Document, group_id: str):
	updates = {field: getattr(parent_doc, field, None) for field in SYNC_FIELDS}
	updates["custom_assignment_group"] = group_id
	frappe.db.set_value("ToDo", child_name, updates, update_modified=False)


def _create_child_todo(parent_doc: Document, user: str, group_id: str):
	child_todo = frappe.new_doc("ToDo")
	child_todo.flags.opero_skip_sync = True

	for field in SYNC_FIELDS:
		setattr(child_todo, field, getattr(parent_doc, field, None))

	if not child_todo.custom_title and child_todo.description:
		child_todo.custom_title = _extract_plain_text(child_todo.description)

	child_todo.allocated_to = user
	child_todo.assigned_by = getattr(parent_doc, "assigned_by", None) or frappe.session.user
	_set_doc_assignees(child_todo, [user])
	child_todo.custom_parent_todo = parent_doc.name
	child_todo.custom_assignment_group = group_id
	child_todo.custom_is_group_child = 1
	child_todo.custom_additional_assignees = ""

	child_todo.insert(ignore_permissions=True)


def _dedupe(users: list[str]) -> list[str]:
	seen: set[str] = set()
	result: list[str] = []
	for user in users:
		if user in seen:
			continue
		seen.add(user)
		result.append(user)

	return result
