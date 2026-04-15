from __future__ import annotations

"""Create the 'Flow Hub' workspace as a sidebar entry point.

The page was renamed from 'flow-hub' to 'opero-flow-hub' so the workspace
can own the /app/flow-hub route without conflict.  A global JS redirect in
opero_global.js transparently forwards workspace visits to the page.

Also updates the ToDo Hub shortcut link to the new page name.
"""

import json

import frappe

WORKSPACE_NAME = "Flow Hub"
TODO_HUB_WORKSPACE = "ToDo Hub"
REPORT_ACTION_QUEUE = "ToDo Action Queue"
REPORT_ASSIGNEE_LOAD = "ToDo Assignee Load and Risk"
REPORT_IN_PROGRESS_AGING = "ToDo In Progress Aging"
REPORT_CREATED_CLOSED = "ToDo Created vs Closed 30d"


def execute():
	_create_flow_hub_workspace()
	_fix_todo_hub_shortcut()
	frappe.clear_cache(doctype="Workspace")


def _create_flow_hub_workspace():
	doc = _get_or_new_workspace(WORKSPACE_NAME)

	doc.update(
		{
			"title": WORKSPACE_NAME,
			"label": WORKSPACE_NAME,
			"icon": "fa fa-random",
			"indicator_color": "cyan",
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
				"link_to": "opero-flow-hub",
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

	_ensure_route_name(doc, WORKSPACE_NAME)


def _fix_todo_hub_shortcut():
	"""Update the 'Open Flow Hub' shortcut in ToDo Hub to point to the renamed page."""
	if not frappe.db.exists("Workspace", TODO_HUB_WORKSPACE):
		return

	doc = frappe.get_doc("Workspace", TODO_HUB_WORKSPACE)
	updated = False
	for shortcut in doc.shortcuts:
		if shortcut.link_to == "flow-hub" and shortcut.type == "Page":
			shortcut.link_to = "opero-flow-hub"
			updated = True

	if updated:
		doc.save(ignore_permissions=True)


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


def _get_or_new_workspace(name):
	if frappe.db.exists("Workspace", name):
		return frappe.get_doc("Workspace", name)

	existing = frappe.db.get_value("Workspace", {"label": name}, "name")
	if existing:
		return frappe.get_doc("Workspace", existing)

	return frappe.get_doc({"doctype": "Workspace", "label": name})


def _ensure_route_name(doc, target_name):
	if doc.name == target_name:
		return
	if frappe.db.exists("Workspace", target_name):
		return
	frappe.rename_doc("Workspace", doc.name, target_name, force=True)


def _get_next_workspace_sequence() -> float:
	rows = frappe.get_all(
		"Workspace",
		filters={"public": 1},
		fields=["max(sequence_id) as max_sequence"],
	)
	max_val = (rows[0].max_sequence if rows and rows[0].max_sequence is not None else 0) or 0
	return float(max_val) + 1
