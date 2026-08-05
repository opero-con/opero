"""Comment handlers ported from FC Server Scripts."""

from __future__ import annotations

import frappe


def on_update_comment(doc, _method=None):
	if doc.comment_type != "Comment" or doc.reference_doctype != "ToDo" or not doc.reference_name:
		return

	content = doc.content or ""
	mentions = []
	start = 0
	key = 'data-id="'
	while True:
		id_index = content.find(key, start)
		if id_index == -1:
			break
		start_quote = id_index + len(key)
		end_quote = content.find('"', start_quote)
		if end_quote == -1:
			break
		user_id = content[start_quote:end_quote].strip()
		if user_id and user_id not in mentions:
			mentions.append(user_id)
		start = end_quote + 1

	todo = frappe.get_doc("ToDo", doc.reference_name)
	for user_id in mentions:
		if user_id == todo.owner or user_id.lower() == "administrator":
			continue
		if not frappe.db.exists("User", user_id):
			continue
		user_doc = frappe.get_doc("User", user_id)
		if not user_doc.enabled:
			continue
		if frappe.db.exists(
			"DocShare",
			{"share_doctype": "ToDo", "share_name": doc.reference_name, "user": user_id},
		):
			continue
		frappe.get_doc(
			{
				"doctype": "DocShare",
				"user": user_id,
				"share_doctype": "ToDo",
				"share_name": doc.reference_name,
				"read": 1,
				"write": 0,
				"share": 1,
			}
		).insert(ignore_permissions=True)
