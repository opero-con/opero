// Run with: node --test opero/tests/timesheet_client.test.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const moment = require(process.env.FRAPPE_MOMENT_PATH || "../../../frappe/node_modules/moment");

function loadForm(allocationBalances = [], allocationRequest = null, dailyRequest = async () => []) {
	const handlers = [];
	const rows = new Map();
	const dashboardSections = [];
	let linksAreaHidden = false;
	const frappe = {
		ui: { form: { on: (doctype, events) => handlers.push({ doctype, events }) } },
		utils: { debounce: (fn) => fn, escape_html: (value) => String(value || "") },
		db: {
			get_value: async (doctype, name, fieldname) => ({
				message: { [fieldname]: `Subject ${name}` },
			}),
			get_list: async () => [],
		},
		get_meta: () => ({
			fields: [
				"task",
				"project",
				"description",
				"is_billable",
				"activity_type",
				"zoho_entry_id",
				"custom_week_of_month",
				"custom_zoho_sync_uncertain",
			].map((fieldname) => ({ fieldname })),
		}),
		get_doc: (doctype, name) => rows.get(name),
		model: {
			set_value: async (doctype, name, values, value) =>
				Object.assign(
					rows.get(name),
					typeof values === "string" ? { [values]: value } : values
				),
		},
		xcall: async (method, args) =>
			method === "opero.api.timesheet.preview_daily_times" ? dailyRequest(args) :
			method === "opero.api.timesheet.get_allocation_balances"
				? allocationRequest
					? allocationRequest()
					: allocationBalances
				: 0,
	};
	const context = { frappe, moment, __: (value) => value, document: {}, setTimeout };
	vm.createContext(context);
	vm.runInContext(
		fs.readFileSync(path.join(__dirname, "../public/js/custom/timesheet.js"), "utf8"),
		context
	);
	const buttons = new Map();
	const hiddenFields = new Set();
	const frm = {
		doc: { docstatus: 0, time_logs: [] },
		dashboard: {
			links_area: { hide: () => (linksAreaHidden = true) },
			parent: { find: () => ({ remove() {} }) },
			show() {},
			add_section: (...args) => dashboardSections.push(args),
		},
		add_custom_button: (label, action) => buttons.set(label, action),
		add_child: (table, values) => {
			const row = { ...values, doctype: "Timesheet Detail", name: "new-" + rows.size };
			frm.doc.time_logs.push(row);
			rows.set(row.name, row);
			return row;
		},
		toggle_display: (fieldname, show) => {
			if (!show) hiddenFields.add(fieldname);
		},
		set_query() {},
		refresh_field() {},
		dirty() {},
		set_value: async (fieldname, value) => {
			frm.doc[fieldname] = value;
		},
		is_new: () => true,
	};
	return {
		handlers,
		rows,
		frm,
		buttons,
		hiddenFields,
		dashboardSections,
		linksAreaHidden: () => linksAreaHidden,
	};
}

test("Timesheet hides report-only and unused fields on the form", async () => {
	const { handlers, frm, hiddenFields, linksAreaHidden } = loadForm();
	for (const { doctype, events } of handlers)
		if (doctype === "Timesheet" && events.refresh) await events.refresh(frm);
	assert.equal(hiddenFields.has("employee_name"), true);
	assert.equal(hiddenFields.has("workflow_state"), true);
	assert.equal(hiddenFields.has("department"), true);
	assert.equal(hiddenFields.has("custom_total_spent_hours"), true);
	assert.equal(hiddenFields.has("custom_pm_name"), true);
	assert.equal(linksAreaHidden(), true);
});

test("selecting a task appends its subject to Notes once", async () => {
	const { handlers, rows, frm } = loadForm();
	frm.doc.note = "<p>Existing note</p>";
	const row = {
		doctype: "Timesheet Detail",
		name: "task-note-row",
		task: "TASK-1",
		custom_project_task: "Design",
	};
	frm.doc.time_logs.push(row);
	rows.set(row.name, row);
	const taskHandler = handlers.find(
		({ doctype, events }) =>
			doctype === "Timesheet Detail" && String(events.task).includes("append_task_to_notes")
	);

	await taskHandler.events.task(frm, row.doctype, row.name);
	await taskHandler.events.task(frm, row.doctype, row.name);

	assert.equal(frm.doc.note, "<p>Existing note</p><p>Design: </p>");
});

test("task Notes fallback uses the Task subject", async () => {
	const { handlers, rows, frm } = loadForm();
	const row = { doctype: "Timesheet Detail", name: "task-note-fallback", task: "TASK-2" };
	frm.doc.time_logs.push(row);
	rows.set(row.name, row);
	const taskHandler = handlers.find(
		({ doctype, events }) =>
			doctype === "Timesheet Detail" && String(events.task).includes("append_task_to_notes")
	);

	await taskHandler.events.task(frm, row.doctype, row.name);

	assert.equal(frm.doc.note, "<p>Subject TASK-2: </p>");
});
test("allocation summary uses concise labels", async () => {
	const { handlers, frm, dashboardSections } = loadForm([
		{
			task: "TASK-1",
			task_name: "Design",
			month: "Sep 2026",
			allocated: 10,
			submitted: 3,
			current: 2,
			remaining: 5,
		},
	]);
	Object.assign(frm.doc, { employee: "EMP-1", parent_project: "PROJ-1" });
	const handler = handlers.find(
		({ doctype, events }) =>
			doctype === "Timesheet" && String(events.refresh).includes("get_allocation_balances")
	);

	await handler.events.refresh(frm);

	assert.equal(dashboardSections.length, 2);
	assert.match(dashboardSections[0][0], /Loading allocations/);
	const [html, title] = dashboardSections.at(-1);
	assert.equal(title, "Allocations");
	for (const heading of ["Task / Month", "Allocated", "Submitted", "This sheet", "Remaining"]) {
		assert.match(html, new RegExp(`<th>${heading}</th>`));
	}
	assert.doesNotMatch(html, /Remaining after this timesheet|This timesheet/);
});

test("allocation summary is available on submitted sheets without a parent project", async () => {
	const { handlers, frm, dashboardSections } = loadForm([
		{
			task: "TASK-1",
			task_name: "Design",
			month: "Sep 2026",
			allocated: 10,
			submitted: 3,
			current: 2,
			remaining: 5,
		},
	]);
	Object.assign(frm.doc, {
		docstatus: 1,
		employee: "EMP-1",
		parent_project: null,
		time_logs: [{ task: "TASK-1", project: "PROJ-1", from_time: "2026-09-10", hours: 2 }],
	});
	const handler = handlers.find(
		({ doctype, events }) =>
			doctype === "Timesheet" && String(events.refresh).includes("get_allocation_balances")
	);

	await handler.events.refresh(frm);

	assert.match(dashboardSections.at(-1)[0], /Design/);
});
test("allocation summary shows an empty state for incomplete rows", async () => {
	const { handlers, frm, dashboardSections } = loadForm();
	Object.assign(frm.doc, { employee: "EMP-1", parent_project: "PROJ-1" });
	const handler = handlers.find(
		({ doctype, events }) =>
			doctype === "Timesheet" && String(events.refresh).includes("get_allocation_balances")
	);

	await handler.events.refresh(frm);

	assert.match(dashboardSections.at(-1)[0], /Add a task and date/);
});

test("allocation summary replaces loading with a recoverable error", async () => {
	const { handlers, frm, dashboardSections } = loadForm([], async () => {
		throw new Error("offline");
	});
	Object.assign(frm.doc, { employee: "EMP-1", parent_project: "PROJ-1" });
	const handler = handlers.find(
		({ doctype, events }) =>
			doctype === "Timesheet" && String(events.refresh).includes("get_allocation_balances")
	);

	await handler.events.refresh(frm);

	assert.match(dashboardSections.at(-1)[0], /Could not load allocations/);
	assert.match(dashboardSections.at(-1)[0], /text-danger/);
});

test("allocation summary ignores an older response", async () => {
	const pending = [];
	const { handlers, frm, dashboardSections } = loadForm(
		[],
		() => new Promise((resolve) => pending.push(resolve))
	);
	Object.assign(frm.doc, { employee: "EMP-1", parent_project: "PROJ-1" });
	const handler = handlers.find(
		({ doctype, events }) =>
			doctype === "Timesheet" && String(events.refresh).includes("get_allocation_balances")
	);

	const first = handler.events.refresh(frm);
	const second = handler.events.refresh(frm);
	pending[1]([
		{
			task: "NEW",
			task_name: "Newest",
			month: "Sep 2026",
			allocated: 8,
			submitted: 1,
			current: 2,
			remaining: 5,
		},
	]);
	await second;
	pending[0]([
		{
			task: "OLD",
			task_name: "Stale",
			month: "Sep 2026",
			allocated: 8,
			submitted: 1,
			current: 2,
			remaining: 5,
		},
	]);
	await first;

	assert.match(dashboardSections.at(-1)[0], /Newest/);
	assert.doesNotMatch(dashboardSections.at(-1)[0], /Stale/);
});
test("draft forms do not offer midnight splitting", async () => {
	const { handlers, frm, buttons } = loadForm();
	for (const { doctype, events } of handlers)
		if (doctype === "Timesheet" && events.refresh) await events.refresh(frm);
	assert.equal(buttons.has("Split at midnight"), false);
});

test("submitted forms do not offer splitting", async () => {
	const { handlers, frm, buttons } = loadForm();
	frm.doc.docstatus = 1;
	for (const { doctype, events } of handlers)
		if (doctype === "Timesheet" && events.refresh) await events.refresh(frm);
	assert.equal(buttons.has("Split at midnight"), false);
});

test("pending syncs can be retried after an interrupted worker", async () => {
	const { handlers, frm, buttons } = loadForm();
	frm.doc.docstatus = 1;
	frm.doc.custom_zoho_sync_status = "Pending";
	for (const { doctype, events } of handlers)
		if (doctype === "Timesheet" && events.refresh) await events.refresh(frm);
	assert.equal(buttons.has("Retry Zoho sync"), true);
});

test("week updates from From Time and clears when the date is removed", async () => {
	const { handlers, rows, frm } = loadForm();
	const row = { doctype: "Timesheet Detail", name: "week-test", custom_week_of_month: "wrong" };
	rows.set(row.name, row);
	for (const [date, week] of [
		["2026-09-06 23:00:00", "Week 1"],
		["2026-09-07 00:00:00", "Week 2"],
		["2026-09-08 00:00:00", "Week 2"],
		["2026-09-14 00:00:00", "Week 3"],
		["2026-09-22 09:00:00", "Week 4"],
		["2024-02-29 09:00:00", "Week 5"],
		["2026-03-30 00:00:00", "Week 6"],
		[null, ""],
	]) {
		row.from_time = date;
		for (const { doctype, events } of handlers)
			if (doctype === "Timesheet Detail" && events.from_time) {
				await events.from_time(frm, row.doctype, row.name);
			}
		assert.equal(row.custom_week_of_month, week);
	}
});


test("seven-hour preview keeps one task row and its billing hours", async () => {
	let request;
	const { handlers, frm, rows } = loadForm([], null, async (args) => {
		request = args;
		return [{ name: "late-entry", from_time: "2026-10-09 08:30:00", to_time: "2026-10-09 15:30:00" }];
	});
	frm.doc.employee = "EMP-1";
	frm.doc.name = "TS264001";
	frm.is_new = () => false;
	const row = { name: "late-entry", doctype: "Timesheet Detail", from_time: "2026-10-09 22:00:00", to_time: "2026-10-10 05:00:00", hours: 7, billing_hours: 7, task: "TASK-1" };
	frm.doc.time_logs.push(row);
	rows.set(row.name, row);
	const handler = handlers.find(({ doctype, events }) => doctype === "Timesheet Detail" && String(events.hours).includes("schedule_daily_times"));
	handler.events.hours(frm);
	await new Promise((resolve) => setImmediate(resolve));
	assert.equal(row.from_time, "2026-10-09 08:30:00");
	assert.equal(row.to_time, "2026-10-09 15:30:00");
	assert.equal(row.hours, 7);
	assert.equal(row.billing_hours, 7);
	assert.equal(frm.doc.time_logs.length, 1);
	assert.equal(row.task, "TASK-1");
	assert.equal(request.timesheet_name, "TS264001");
});

test("scheduling preview ignores an older response after hours change", async () => {
	const pending = [];
	const { handlers, frm, rows } = loadForm([], null, () => new Promise((resolve) => pending.push(resolve)));
	frm.doc.employee = "EMP-1";
	const row = { name: "entry", doctype: "Timesheet Detail", from_time: "2026-10-09 22:00:00", hours: 5 };
	frm.doc.time_logs.push(row);
	rows.set(row.name, row);
	const handler = handlers.find(({ doctype, events }) => doctype === "Timesheet Detail" && String(events.hours).includes("schedule_daily_times"));
	handler.events.hours(frm);
	row.hours = 2;
	handler.events.hours(frm);
	pending[1]([{ name: "entry", from_time: "2026-10-09 08:00:00", to_time: "2026-10-09 10:00:00" }]);
	await new Promise((resolve) => setImmediate(resolve));
	pending[0]([{ name: "entry", from_time: "2026-10-09 08:00:00", to_time: "2026-10-09 13:00:00" }]);
	await new Promise((resolve) => setImmediate(resolve));
	assert.equal(row.to_time, "2026-10-09 10:00:00");
	assert.equal(row.hours, 2);
});


test("Project choices follow the selected personnel and customer", async () => {
	const { handlers, frm } = loadForm();
	let query;
	frm.set_query = (field, handler) => { if (field === "parent_project") query = handler; };
	for (const { doctype, events } of handlers)
		if (doctype === "Timesheet" && events.refresh) await events.refresh(frm);
	assert.equal(query().filters.employee, undefined);
	frm.doc.employee = "EMP-1";
	frm.doc.customer = "CUSTOMER-1";
	assert.equal(query().query, "opero.api.timesheet.get_personnel_projects");
	assert.equal(query().filters.employee, "EMP-1");
	assert.equal(query().filters.customer, "CUSTOMER-1");
	frm.doc.employee = "EMP-2";
	assert.equal(query().filters.employee, "EMP-2");
});
