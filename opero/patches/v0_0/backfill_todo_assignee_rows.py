from __future__ import annotations

import re

import frappe


USER_TOKEN_SPLIT = re.compile(r"[\n,;]+")


def execute():
	if not frappe.db.exists("DocType", "ToDo Assignee"):
		return

	enabled_users = set(frappe.get_all("User", filters={"enabled": 1}, pluck="name"))
	todos = frappe.get_all("ToDo", fields=["name", "allocated_to", "custom_additional_assignees"])

	for todo in todos:
		users = _get_existing_row_users(todo.name)
		primary = (todo.allocated_to or "").strip()
		if primary:
			users.append(primary)

		users.extend(_parse_users(todo.custom_additional_assignees))
		users = [user for user in _dedupe(users) if user in enabled_users]
		_set_assignee_rows(todo.name, users)
		frappe.db.set_value(
			"ToDo",
			todo.name,
			{
				"allocated_to": users[0] if users else None,
				"custom_additional_assignees": "\n".join(users[1:]),
			},
			update_modified=False,
		)


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


def _get_existing_row_users(todo_name: str) -> list[str]:
	return [
		row.user
		for row in frappe.get_all(
			"ToDo Assignee",
			filters={"parent": todo_name, "parenttype": "ToDo", "parentfield": "custom_assignees"},
			fields=["user"],
			order_by="idx asc",
		)
		if row.user
	]


def _parse_users(raw_value: str | None) -> list[str]:
	if not raw_value:
		return []

	return [token.strip() for token in USER_TOKEN_SPLIT.split(raw_value) if token.strip()]


def _dedupe(users: list[str]) -> list[str]:
	seen: set[str] = set()
	result: list[str] = []
	for user in users:
		if user in seen:
			continue
		seen.add(user)
		result.append(user)
	return result
