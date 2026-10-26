"""Apply the Task, From Time and Hrs defaults to existing users once."""

import json

import frappe
from frappe.model.utils.user_settings import sync_user_settings


def execute():
	# Flush cached selections first so they cannot restore the obsolete columns.
	sync_user_settings()
	rows = frappe.db.sql(
		"select `user`, `data` from `__UserSettings` where `doctype`=%s",
		"Timesheet",
		as_dict=True,
	)
	for row in rows:
		data = json.loads(row.data or "{}")
		if data.get("GridView", {}).pop("Timesheet Detail", None) is None:
			continue
		frappe.db.sql(
			"update `__UserSettings` set `data`=%s where `user`=%s and `doctype`=%s",
			(json.dumps(data), row.user, "Timesheet"),
		)
	frappe.cache.delete_value("_user_settings")
