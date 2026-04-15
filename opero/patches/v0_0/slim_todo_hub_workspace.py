from __future__ import annotations

"""Replace the ToDo Hub workspace's number cards and charts with a single
Flow Hub page shortcut.  The custom Page already provides a richer,
single-request view of the same metrics, so the workspace becomes a
lightweight navigation hub: one prominent link to Flow Hub plus direct
shortcuts to each report.
"""

import json

import frappe

WORKSPACE_NAME = "ToDo Hub"
REPORT_ACTION_QUEUE = "ToDo Action Queue"
REPORT_CREATED_CLOSED = "ToDo Created vs Closed 30d"
REPORT_ASSIGNEE_LOAD = "ToDo Assignee Load and Risk"
REPORT_IN_PROGRESS_AGING = "ToDo In Progress Aging"


def execute():
	if not frappe.db.exists("Workspace", WORKSPACE_NAME):
		return

	doc = frappe.get_doc("Workspace", WORKSPACE_NAME)

	# Drop all number cards and dashboard charts — Flow Hub renders these
	doc.set("number_cards", [])
	doc.set("charts", [])

	doc.set(
		"shortcuts",
		[
			{
				"type": "Page",
				"link_to": "flow-hub",
				"label": "Flow Hub",
			},
			{
				"type": "DocType",
				"link_to": "ToDo",
				"doc_view": "New",
				"label": "New ToDo",
			},
			{
				"type": "Report",
				"link_to": REPORT_ACTION_QUEUE,
				"label": "My ToDos",
			},
			{
				"type": "Report",
				"link_to": REPORT_ASSIGNEE_LOAD,
				"label": "Team Load & Risk",
			},
			{
				"type": "Report",
				"link_to": REPORT_IN_PROGRESS_AGING,
				"label": "In Progress Aging",
			},
		],
	)

	doc.set(
		"links",
		[
			{
				"type": "Card Break",
				"label": "ToDo Reports",
				"hidden": 0,
				"link_count": 5,
			},
			{
				"type": "Link",
				"label": REPORT_ACTION_QUEUE,
				"link_type": "Report",
				"link_to": REPORT_ACTION_QUEUE,
				"is_query_report": 1,
			},
			{
				"type": "Link",
				"label": REPORT_CREATED_CLOSED,
				"link_type": "Report",
				"link_to": REPORT_CREATED_CLOSED,
				"is_query_report": 1,
			},
			{
				"type": "Link",
				"label": REPORT_ASSIGNEE_LOAD,
				"link_type": "Report",
				"link_to": REPORT_ASSIGNEE_LOAD,
				"is_query_report": 1,
			},
			{
				"type": "Link",
				"label": REPORT_IN_PROGRESS_AGING,
				"link_type": "Report",
				"link_to": REPORT_IN_PROGRESS_AGING,
				"is_query_report": 1,
			},
			{
				"type": "Link",
				"label": "ToDo",
				"link_type": "DocType",
				"link_to": "ToDo",
				"is_query_report": 0,
			},
		],
	)

	doc.content = json.dumps(_workspace_content(), separators=(",", ":"))
	doc.save(ignore_permissions=True)

	frappe.clear_cache(doctype="Workspace")


def _workspace_content():
	return [
		{
			"id": "todo-hub-s0",
			"type": "shortcut",
			"data": {"shortcut_name": "Flow Hub", "col": 4},
		},
		{
			"id": "todo-hub-s1",
			"type": "shortcut",
			"data": {"shortcut_name": "New ToDo", "col": 2},
		},
		{
			"id": "todo-hub-s2",
			"type": "shortcut",
			"data": {"shortcut_name": "My ToDos", "col": 2},
		},
		{
			"id": "todo-hub-s3",
			"type": "shortcut",
			"data": {"shortcut_name": "Team Load & Risk", "col": 2},
		},
		{
			"id": "todo-hub-s4",
			"type": "shortcut",
			"data": {"shortcut_name": "In Progress Aging", "col": 2},
		},
		{"id": "todo-hub-sp1", "type": "spacer", "data": {"col": 12}},
		{
			"id": "todo-hub-r1",
			"type": "card",
			"data": {"card_name": "ToDo Reports", "col": 4},
		},
	]
