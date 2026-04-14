from __future__ import annotations

import re

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


USER_TOKEN_SPLIT = re.compile(r"[\n,;]+")


def execute():
	legacy_assignees, has_legacy_additional_column = _load_legacy_assignees()
	ensure_assignee_field_type()
	seed_assignee_rows(legacy_assignees, has_legacy_additional_column)


def ensure_assignee_field_type():
	create_custom_fields(
		{
			"ToDo": [
				{
					"fieldname": "custom_assignees",
					"label": "Assignees",
					"fieldtype": "Table MultiSelect",
					"options": "ToDo Assignee",
					"insert_after": "custom_title",
					"description": "Select one or more users to assign this task to.",
				},
			]
		},
		ignore_validate=True,
		update=True,
	)


def _load_legacy_assignees() -> tuple[dict[str, list[str]], bool]:
	columns = set(frappe.db.get_table_columns("ToDo"))
	select_parts = ["name", "allocated_to"]
	has_legacy_text_column = "custom_assignees" in columns
	has_legacy_additional_column = "custom_additional_assignees" in columns
	if has_legacy_text_column:
		select_parts.append("custom_assignees")
	if has_legacy_additional_column:
		select_parts.append("custom_additional_assignees")

	records = frappe.get_all("ToDo", fields=select_parts)
	enabled_users = set(frappe.get_all("User", filters={"enabled": 1}, pluck="name"))
	assignee_map: dict[str, list[str]] = {}

	for row in records:
		users = []
		primary = (row.allocated_to or "").strip()
		if primary:
			users.append(primary)

		if has_legacy_text_column:
			users.extend(_parse_text_users(getattr(row, "custom_assignees", None)))

		if has_legacy_additional_column:
			users.extend(_parse_text_users(getattr(row, "custom_additional_assignees", None)))
		users = [user for user in _dedupe(users) if user in enabled_users]
		assignee_map[row.name] = users

	return assignee_map, has_legacy_additional_column


def seed_assignee_rows(assignee_map: dict[str, list[str]], has_legacy_additional_column: bool):
	for todo_name, users in assignee_map.items():
		_set_assignee_rows(todo_name, users)
		updates = {
			"allocated_to": users[0] if users else None,
		}
		if has_legacy_additional_column:
			updates["custom_additional_assignees"] = "\n".join(users[1:])

		frappe.db.set_value("ToDo", todo_name, updates, update_modified=False)


def _set_assignee_rows(todo_name: str, users: list[str]):
	frappe.db.delete("ToDo Assignee", {"parenttype": "ToDo", "parentfield": "custom_assignees", "parent": todo_name})
	for idx, user in enumerate(users, start=1):
		frappe.get_doc(
			{
				"doctype": "ToDo Assignee",
				"parenttype": "ToDo",
				"parentfield": "custom_assignees",
				"parent": todo_name,
				"idx": idx,
				"user": user,
			}
		).insert(ignore_permissions=True)


def _parse_text_users(raw_values: str | None) -> list[str]:
	if not raw_values:
		return []
	return [token.strip() for token in USER_TOKEN_SPLIT.split(raw_values) if token.strip()]


def _dedupe(users: list[str]) -> list[str]:
	seen: set[str] = set()
	result: list[str] = []
	for user in users:
		if user in seen:
			continue
		seen.add(user)
		result.append(user)
	return result
