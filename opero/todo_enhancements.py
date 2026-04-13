from __future__ import annotations

import re
from collections.abc import Iterable

import frappe
from frappe.model.document import Document


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
	return bool(getattr(doc.flags, "opero_skip_sync", False) or getattr(doc, "custom_is_group_child", 0))


def _sync_title_and_description(doc: Document):
	title = (getattr(doc, "custom_title", None) or "").strip()
	description = (getattr(doc, "description", None) or "").strip()

	if title and not description:
		doc.description = title
	elif description and not title:
		doc.custom_title = description


def _normalize_assignees(doc: Document):
	primary = (getattr(doc, "allocated_to", None) or "").strip()
	additional = _parse_assignees(getattr(doc, "custom_additional_assignees", None))

	if not primary and additional:
		primary = additional.pop(0)
		doc.allocated_to = primary

	additional = [user for user in additional if user != primary]
	valid_additional = _filter_existing_enabled_users(additional)
	doc.custom_additional_assignees = "\n".join(valid_additional)


def _parse_assignees(raw_values: str | None) -> list[str]:
	if not raw_values:
		return []

	seen: set[str] = set()
	normalized: list[str] = []
	for token in USER_TOKEN_SPLIT.split(raw_values):
		user = token.strip()
		if not user or user in seen:
			continue

		seen.add(user)
		normalized.append(user)

	return normalized


def _filter_existing_enabled_users(users: Iterable[str]) -> list[str]:
	users = [user for user in users if user]
	if not users:
		return []

	existing = set(
		frappe.get_all(
			"User",
			filters={"name": ("in", users), "enabled": 1},
			pluck="name",
		)
	)
	return [user for user in users if user in existing]


def _ensure_assignment_group(doc: Document) -> str:
	group_id = (getattr(doc, "custom_assignment_group", None) or "").strip() or doc.name
	if not group_id:
		return ""

	if getattr(doc, "custom_assignment_group", None) != group_id:
		doc.custom_assignment_group = group_id
		frappe.db.set_value("ToDo", doc.name, "custom_assignment_group", group_id, update_modified=False)

	return group_id


def _get_desired_secondary_assignees(doc: Document) -> list[str]:
	primary = (getattr(doc, "allocated_to", None) or "").strip()
	additional = _parse_assignees(getattr(doc, "custom_additional_assignees", None))
	return [user for user in additional if user and user != primary]


def _sync_child_values(child_name: str, parent_doc: Document, group_id: str):
	updates = {field: getattr(parent_doc, field, None) for field in SYNC_FIELDS}
	updates["custom_assignment_group"] = group_id
	frappe.db.set_value("ToDo", child_name, updates, update_modified=False)


def _create_child_todo(parent_doc: Document, user: str, group_id: str):
	child_todo = frappe.new_doc("ToDo")
	child_todo.flags.opero_skip_sync = True

	for field in SYNC_FIELDS:
		setattr(child_todo, field, getattr(parent_doc, field, None))

	if not child_todo.description and child_todo.custom_title:
		child_todo.description = child_todo.custom_title
	elif not child_todo.custom_title and child_todo.description:
		child_todo.custom_title = child_todo.description

	child_todo.allocated_to = user
	child_todo.assigned_by = getattr(parent_doc, "assigned_by", None) or frappe.session.user
	child_todo.custom_parent_todo = parent_doc.name
	child_todo.custom_assignment_group = group_id
	child_todo.custom_is_group_child = 1
	child_todo.custom_additional_assignees = ""

	child_todo.insert(ignore_permissions=True)
