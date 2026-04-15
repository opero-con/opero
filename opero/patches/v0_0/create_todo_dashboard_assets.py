from __future__ import annotations

import json

import frappe


WORKSPACE_NAME = "ToDo Hub"
LEGACY_WORKSPACE_NAME = "ToDo Command Center"
REPORT_ACTION_QUEUE = "ToDo Action Queue"
REPORT_CREATED_CLOSED = "ToDo Created vs Closed"
REPORT_ASSIGNEE_LOAD = "ToDo Assignee Load and Risk"
REPORT_IN_PROGRESS_AGING = "ToDo In Progress Aging"

NUMBER_CARDS = [
	{
		"name": "My Overdue ToDos",
		"label": "My Overdue ToDos",
		"type": "Custom",
		"method": "opero.todo_dashboard.get_my_overdue_todos_count",
		"filters_json": json.dumps({}),
		"dynamic_filters_json": json.dumps({}),
		"color": "#DC2626",
	},
	{
		"name": "My ToDos Due Today",
		"label": "My ToDos Due Today",
		"type": "Custom",
		"method": "opero.todo_dashboard.get_my_todos_due_today_count",
		"filters_json": json.dumps({}),
		"dynamic_filters_json": json.dumps({}),
		"color": "#D97706",
	},
	{
		"name": "My ToDos Due Next 3 Days",
		"label": "My ToDos Due Next 3 Days",
		"type": "Custom",
		"method": "opero.todo_dashboard.get_todo_due_next_days_count",
		"filters_json": json.dumps({"window_days": 3}),
		"dynamic_filters_json": json.dumps({}),
		"color": "#2563EB",
	},
	{
		"name": "My Stale In Progress (7d+)",
		"label": "My Stale In Progress (7d+)",
		"type": "Custom",
		"method": "opero.todo_dashboard.get_todo_stale_in_progress_count",
		"filters_json": json.dumps({"stale_days": 7}),
		"dynamic_filters_json": json.dumps({}),
		"color": "#7C3AED",
	},
	{
		"name": "My In Progress ToDos",
		"label": "My In Progress ToDos",
		"type": "Custom",
		"method": "opero.todo_dashboard.get_my_in_progress_todos_count",
		"filters_json": json.dumps({}),
		"dynamic_filters_json": json.dumps({}),
		"color": "#1D4ED8",
	},
	{
		"name": "Unassigned Active ToDos",
		"label": "Unassigned Active ToDos",
		"type": "Document Type",
		"document_type": "ToDo",
		"function": "Count",
		"filters_json": json.dumps(
			[
				["ToDo", "status", "in", ["Open", "In Progress"]],
				["ToDo", "allocated_to", "is", "not set"],
			]
		),
		"dynamic_filters_json": json.dumps([]),
		"color": "#9333EA",
	},
	{
		"name": "On-time Close Rate (30d)",
		"label": "On-time Close Rate (30d)",
		"type": "Custom",
		"method": "opero.todo_dashboard.get_todo_on_time_close_rate",
		"filters_json": json.dumps({}),
		"dynamic_filters_json": json.dumps({}),
		"color": "#059669",
	},
	{
		"name": "Avg Closure Delay (days, 30d)",
		"label": "Avg Closure Delay (days, 30d)",
		"type": "Custom",
		"method": "opero.todo_dashboard.get_todo_avg_closure_delay",
		"filters_json": json.dumps({}),
		"dynamic_filters_json": json.dumps({}),
		"color": "#0F766E",
	},
]

DASHBOARD_CHARTS = [
	{
		"name": "ToDo Created vs Closed (30d)",
		"chart_name": "ToDo Created vs Closed (30d)",
		"chart_type": "Report",
		"report_name": REPORT_CREATED_CLOSED,
		"use_report_chart": 1,
		"type": "Line",
		"is_public": 1,
		"filters_json": json.dumps({}),
		"dynamic_filters_json": json.dumps({}),
		"timeseries": 0,
	},
	{
		"name": "ToDo Status Split",
		"chart_name": "ToDo Status Split",
		"chart_type": "Group By",
		"document_type": "ToDo",
		"group_by_type": "Count",
		"group_by_based_on": "status",
		"number_of_groups": 6,
		"type": "Donut",
		"is_public": 1,
		"filters_json": json.dumps([]),
		"dynamic_filters_json": json.dumps([]),
		"timeseries": 0,
	},
	{
		"name": "ToDo Assignee Risk",
		"chart_name": "ToDo Assignee Risk",
		"chart_type": "Report",
		"report_name": REPORT_ASSIGNEE_LOAD,
		"use_report_chart": 1,
		"type": "Bar",
		"is_public": 1,
		"filters_json": json.dumps({"top_n": 10}),
		"dynamic_filters_json": json.dumps({}),
		"timeseries": 0,
	},
	{
		"name": "ToDo In Progress Aging",
		"chart_name": "ToDo In Progress Aging",
		"chart_type": "Report",
		"report_name": REPORT_IN_PROGRESS_AGING,
		"use_report_chart": 1,
		"type": "Bar",
		"is_public": 1,
		"filters_json": json.dumps({"min_days": 0, "show_all": 1}),
		"dynamic_filters_json": json.dumps({}),
		"timeseries": 0,
	},
]


def execute():
	_ensure_number_cards()
	_ensure_dashboard_charts()
	_ensure_workspace()
	frappe.clear_cache(doctype="Workspace")
	frappe.clear_cache(doctype="Number Card")
	frappe.clear_cache(doctype="Dashboard Chart")


def _ensure_number_cards():
	for card in NUMBER_CARDS:
		doc = _get_or_new_doc("Number Card", card["name"], "label")
		doc.update(
			{
				"label": card["label"],
				"type": card["type"],
				"document_type": card.get("document_type"),
				"function": card.get("function"),
				"method": card.get("method"),
				"filters_json": card.get("filters_json"),
				"dynamic_filters_json": card.get("dynamic_filters_json"),
				"color": card.get("color"),
				"currency": None,
				"show_percentage_stats": 0,
				"is_public": 1,
				"is_standard": 0,
			}
		)
		if doc.type != "Document Type":
			doc.document_type = None
			doc.function = None
		doc.save(ignore_permissions=True)


def _ensure_dashboard_charts():
	for chart in DASHBOARD_CHARTS:
		if chart.get("chart_type") == "Report" and not frappe.db.exists("Report", chart.get("report_name")):
			continue

		doc = _get_or_new_doc("Dashboard Chart", chart["name"], "chart_name")
		doc.update(
			{
				"chart_name": chart["chart_name"],
				"chart_type": chart["chart_type"],
				"report_name": chart.get("report_name"),
				"use_report_chart": chart.get("use_report_chart", 0),
				"document_type": chart.get("document_type"),
				"group_by_type": chart.get("group_by_type"),
				"group_by_based_on": chart.get("group_by_based_on"),
				"number_of_groups": chart.get("number_of_groups"),
				"type": chart.get("type", "Line"),
				"is_public": chart.get("is_public", 1),
				"filters_json": chart.get("filters_json"),
				"dynamic_filters_json": chart.get("dynamic_filters_json"),
				"timeseries": chart.get("timeseries", 0),
				"currency": None,
				"is_standard": 0,
			}
		)

		if doc.chart_type == "Report":
			doc.document_type = None
			doc.group_by_type = None
			doc.group_by_based_on = None
			doc.number_of_groups = 0
		else:
			doc.report_name = None
			doc.use_report_chart = 0

		doc.save(ignore_permissions=True)


def _ensure_workspace():
	workspace_doc = _get_or_new_workspace()
	workspace_doc.update(
		{
			"title": WORKSPACE_NAME,
			"label": WORKSPACE_NAME,
			"icon": "check-square",
			"indicator_color": "blue",
			"module": "Opero",
			"public": 1,
			"for_user": "",
			"is_hidden": 0,
			"hide_custom": 0,
			"parent_page": "",
		}
	)

	if not workspace_doc.sequence_id:
		workspace_doc.sequence_id = _get_next_workspace_sequence()

	workspace_doc.set(
		"number_cards",
		[
			{"number_card_name": "My Overdue ToDos", "label": "My Overdue"},
			{"number_card_name": "My ToDos Due Today", "label": "Due Today"},
			{"number_card_name": "My ToDos Due Next 3 Days", "label": "Due Next 3d"},
			{"number_card_name": "My Stale In Progress (7d+)", "label": "Stale In Progress"},
			{"number_card_name": "My In Progress ToDos", "label": "In Progress"},
			{"number_card_name": "Unassigned Active ToDos", "label": "Unassigned"},
			{"number_card_name": "On-time Close Rate (30d)", "label": "On-time Rate (30d)"},
			{"number_card_name": "Avg Closure Delay (days, 30d)", "label": "Avg Delay (30d)"},
		],
	)

	workspace_doc.set(
		"charts",
		[
			{"chart_name": "ToDo Created vs Closed (30d)", "label": "Created vs Closed"},
			{"chart_name": "ToDo Status Split", "label": "Status Split"},
			{"chart_name": "ToDo Assignee Risk", "label": "Assignee Risk"},
			{"chart_name": "ToDo In Progress Aging", "label": "In Progress Aging"},
		],
	)

	workspace_doc.set(
		"shortcuts",
		[
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
			{
				"type": "Report",
				"link_to": REPORT_ACTION_QUEUE,
				"label": "Overdue ToDos",
			},
		],
	)

	workspace_doc.set(
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

	workspace_doc.set(
		"roles",
		[
			{"role": "Desk User"},
			{"role": "System Manager"},
		],
	)

	workspace_doc.content = json.dumps(_workspace_content(), separators=(",", ":"))
	workspace_doc.save(ignore_permissions=True)
	workspace_doc = _ensure_workspace_route_name(workspace_doc)
	workspace_doc.reload()


def _ensure_workspace_route_name(workspace_doc):
	if workspace_doc.name == WORKSPACE_NAME:
		return workspace_doc

	if frappe.db.exists("Workspace", WORKSPACE_NAME):
		return frappe.get_doc("Workspace", WORKSPACE_NAME)

	frappe.rename_doc(
		"Workspace",
		workspace_doc.name,
		WORKSPACE_NAME,
		force=True,
	)
	return frappe.get_doc("Workspace", WORKSPACE_NAME)


def _workspace_content():
	return [
		{
			"id": "todo-dashboard-h1",
			"type": "header",
			"data": {"text": '<span class="h4"><b>Action Layer</b></span>', "col": 12},
		},
		{
			"id": "todo-dashboard-c1",
			"type": "number_card",
			"data": {"number_card_name": "My Overdue", "col": 3},
		},
		{
			"id": "todo-dashboard-c2",
			"type": "number_card",
			"data": {"number_card_name": "Due Today", "col": 3},
		},
		{
			"id": "todo-dashboard-c3",
			"type": "number_card",
			"data": {"number_card_name": "Due Next 3d", "col": 3},
		},
		{
			"id": "todo-dashboard-c4",
			"type": "number_card",
			"data": {"number_card_name": "Stale In Progress", "col": 3},
		},
		{
			"id": "todo-dashboard-c5",
			"type": "number_card",
			"data": {"number_card_name": "In Progress", "col": 3},
		},
		{
			"id": "todo-dashboard-c6",
			"type": "number_card",
			"data": {"number_card_name": "Unassigned", "col": 3},
		},
		{
			"id": "todo-dashboard-c7",
			"type": "number_card",
			"data": {"number_card_name": "On-time Rate (30d)", "col": 3},
		},
		{
			"id": "todo-dashboard-c8",
			"type": "number_card",
			"data": {"number_card_name": "Avg Delay (30d)", "col": 3},
		},
		{"id": "todo-dashboard-sp1", "type": "spacer", "data": {"col": 12}},
		{
			"id": "todo-dashboard-h2",
			"type": "header",
			"data": {"text": '<span class="h4"><b>Flow and Capacity</b></span>', "col": 12},
		},
		{
			"id": "todo-dashboard-ch1",
			"type": "chart",
			"data": {"chart_name": "Created vs Closed", "col": 6},
		},
		{
			"id": "todo-dashboard-ch2",
			"type": "chart",
			"data": {"chart_name": "Status Split", "col": 6},
		},
		{
			"id": "todo-dashboard-ch3",
			"type": "chart",
			"data": {"chart_name": "Assignee Risk", "col": 8},
		},
		{
			"id": "todo-dashboard-ch4",
			"type": "chart",
			"data": {"chart_name": "In Progress Aging", "col": 4},
		},
		{"id": "todo-dashboard-sp2", "type": "spacer", "data": {"col": 12}},
		{
			"id": "todo-dashboard-h3",
			"type": "header",
			"data": {"text": '<span class="h4"><b>Quick Actions</b></span>', "col": 12},
		},
		{
			"id": "todo-dashboard-s1",
			"type": "shortcut",
			"data": {"shortcut_name": "New ToDo", "col": 2},
		},
		{
			"id": "todo-dashboard-s2",
			"type": "shortcut",
			"data": {"shortcut_name": "My ToDos", "col": 2},
		},
		{
			"id": "todo-dashboard-s3",
			"type": "shortcut",
			"data": {"shortcut_name": "Team Load & Risk", "col": 3},
		},
		{
			"id": "todo-dashboard-s4",
			"type": "shortcut",
			"data": {"shortcut_name": "In Progress Aging", "col": 3},
		},
		{
			"id": "todo-dashboard-s5",
			"type": "shortcut",
			"data": {"shortcut_name": "Overdue ToDos", "col": 2},
		},
		{"id": "todo-dashboard-sp3", "type": "spacer", "data": {"col": 12}},
		{
			"id": "todo-dashboard-h4",
			"type": "header",
			"data": {"text": '<span class="h4"><b>Reports</b></span>', "col": 12},
		},
		{
			"id": "todo-dashboard-r1",
			"type": "card",
			"data": {"card_name": "ToDo Reports", "col": 4},
		},
	]


def _get_or_new_doc(doctype: str, name: str, key_field: str):
	if frappe.db.exists(doctype, name):
		return frappe.get_doc(doctype, name)

	existing_name = frappe.db.get_value(doctype, {key_field: name}, "name")
	if existing_name:
		return frappe.get_doc(doctype, existing_name)

	return frappe.new_doc(doctype)


def _get_or_new_workspace():
	if frappe.db.exists("Workspace", WORKSPACE_NAME):
		return frappe.get_doc("Workspace", WORKSPACE_NAME)

	existing_name = frappe.db.get_value("Workspace", {"label": WORKSPACE_NAME}, "name")
	if not existing_name:
		existing_name = frappe.db.get_value("Workspace", {"title": WORKSPACE_NAME}, "name")
	if not existing_name and frappe.db.exists("Workspace", LEGACY_WORKSPACE_NAME):
		existing_name = LEGACY_WORKSPACE_NAME
	if not existing_name:
		existing_name = frappe.db.get_value("Workspace", {"label": LEGACY_WORKSPACE_NAME}, "name")
	if not existing_name:
		existing_name = frappe.db.get_value("Workspace", {"title": LEGACY_WORKSPACE_NAME}, "name")
	if existing_name:
		return frappe.get_doc("Workspace", existing_name)
	return frappe.get_doc({"doctype": "Workspace", "label": WORKSPACE_NAME})


def _get_next_workspace_sequence() -> float:
	rows = frappe.get_all(
		"Workspace",
		filters={"public": 1},
		fields=["max(sequence_id) as max_sequence"],
	)
	max_sequence = (rows[0].max_sequence if rows and rows[0].max_sequence is not None else 0) or 0
	return float(max_sequence) + 1
