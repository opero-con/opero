from __future__ import annotations

"""Create a 'Flow Hub' workspace that surfaces the Flow Hub page as its
primary entry point, with report shortcuts below.  This gives users a
proper sidebar item named 'Flow Hub' that acts as a one-click launchpad.
"""

import json

import frappe

WORKSPACE_NAME = "Flow Hub"
REPORT_ACTION_QUEUE = "ToDo Action Queue"
REPORT_ASSIGNEE_LOAD = "ToDo Assignee Load and Risk"
REPORT_IN_PROGRESS_AGING = "ToDo In Progress Aging"
REPORT_CREATED_CLOSED = "ToDo Created vs Closed 30d"


def execute():
	doc = _get_or_new_workspace()

	doc.update(
		{
			"title": WORKSPACE_NAME,
			"label": WORKSPACE_NAME,
			"icon": "fa fa-random",
			"indicator_color": "teal",
			"module": "Opero",
			"public": 1,
			"for_user": "",
			"is_hidden": 0,
			"hide_custom": 0,
			"parent_page": "",
		}
	)

	if not doc.sequence_id:
		doc.sequence_id = _get_next_workspace_sequence()

	doc.set(
		"shortcuts",
		[
			{
				"type": "Page",
				"link_to": "flow-hub",
				"label": "Open Flow Hub",
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

	doc.set("number_cards", [])
	doc.set("charts", [])

	doc.set(
		"links",
		[
			{
				"type": "Card Break",
				"label": "ToDo Reports",
				"hidden": 0,
				"link_count": 4,
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

	doc.set(
		"roles",
		[
			{"role": "Desk User"},
			{"role": "System Manager"},
		],
	)

	doc.content = json.dumps(_workspace_content(), separators=(",", ":"))
	doc.save(ignore_permissions=True)

	_ensure_route_name(doc)
	frappe.clear_cache(doctype="Workspace")


def _workspace_content():
	return [
		{
			"id": "fh-h1",
			"type": "header",
			"data": {
				"text": '<span class="h4"><b>Flow Hub</b></span>',
				"col": 12,
			},
		},
		{
			"id": "fh-s0",
			"type": "shortcut",
			"data": {"shortcut_name": "Open Flow Hub", "col": 12},
		},
		{"id": "fh-sp1", "type": "spacer", "data": {"col": 12}},
		{
			"id": "fh-h2",
			"type": "header",
			"data": {
				"text": '<span class="h4"><b>Quick Actions</b></span>',
				"col": 12,
			},
		},
		{
			"id": "fh-s1",
			"type": "shortcut",
			"data": {"shortcut_name": "New ToDo", "col": 3},
		},
		{
			"id": "fh-s2",
			"type": "shortcut",
			"data": {"shortcut_name": "My ToDos", "col": 3},
		},
		{
			"id": "fh-s3",
			"type": "shortcut",
			"data": {"shortcut_name": "Team Load & Risk", "col": 3},
		},
		{
			"id": "fh-s4",
			"type": "shortcut",
			"data": {"shortcut_name": "In Progress Aging", "col": 3},
		},
		{"id": "fh-sp2", "type": "spacer", "data": {"col": 12}},
		{
			"id": "fh-h3",
			"type": "header",
			"data": {
				"text": '<span class="h4"><b>Reports</b></span>',
				"col": 12,
			},
		},
		{
			"id": "fh-r1",
			"type": "card",
			"data": {"card_name": "ToDo Reports", "col": 4},
		},
	]


def _get_or_new_workspace():
	if frappe.db.exists("Workspace", WORKSPACE_NAME):
		return frappe.get_doc("Workspace", WORKSPACE_NAME)

	existing_name = frappe.db.get_value("Workspace", {"label": WORKSPACE_NAME}, "name")
	if not existing_name:
		existing_name = frappe.db.get_value("Workspace", {"title": WORKSPACE_NAME}, "name")
	if existing_name:
		return frappe.get_doc("Workspace", existing_name)

	return frappe.get_doc({"doctype": "Workspace", "label": WORKSPACE_NAME})


def _ensure_route_name(doc):
	if doc.name == WORKSPACE_NAME:
		return

	if frappe.db.exists("Workspace", WORKSPACE_NAME):
		return

	frappe.rename_doc("Workspace", doc.name, WORKSPACE_NAME, force=True)


def _get_next_workspace_sequence() -> float:
	rows = frappe.get_all(
		"Workspace",
		filters={"public": 1},
		fields=["max(sequence_id) as max_sequence"],
	)
	max_sequence = (rows[0].max_sequence if rows and rows[0].max_sequence is not None else 0) or 0
	return float(max_sequence) + 1
