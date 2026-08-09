"""Keep desk notification panels free of email HTML bodies.

Frappe mirrors `email_content` into `Notification Log.description` when
description is empty. Opero's Travel Request email rules previously left
`notification_message` blank, so the full email HTML landed in the bell
dropdown and broke layout under reyal_core's notification chrome.
"""

from __future__ import annotations

import frappe

DESK_MESSAGES = {
	"Travel Request Awaiting Your Approval": (
		"{{ doc.employee_name }} · {{ doc.custom_project_name }} · "
		'{{ doc.workflow_state or "Pending Approval" }}'
	),
	"Travel Request Updated - Review Required": (
		"{{ doc.employee_name }} · {{ doc.custom_project_name }} · "
		'{{ doc.workflow_state or "Updated" }}'
	),
	"Travel Request Approval - Review Details": (
		"{{ doc.employee_name }} · {{ doc.custom_project_name }} · "
		'{{ doc.workflow_state or "Approved" }}'
	),
	"System - Timesheet Approval": (
		"{{ doc.employee_name or doc.owner }} · Timesheet pending approval"
	),
}


def execute():
	for name, message in DESK_MESSAGES.items():
		if not frappe.db.exists("Notification", name):
			continue
		frappe.db.set_value(
			"Notification",
			name,
			"notification_message",
			message,
			update_modified=False,
		)

	# Existing logs already copied the email HTML into description; clear those
	# so the dropdown shows the short subject again.
	frappe.db.sql(
		"""
		UPDATE `tabNotification Log`
		SET description = NULL
		WHERE document_type = 'Travel Request'
			AND description IS NOT NULL
			AND description != ''
			AND (
				description LIKE '%%<ul>%%'
				OR description LIKE '%%Details:%%'
				OR description LIKE '%%<p>%%'
			)
		"""
	)
