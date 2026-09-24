// Run with: node --test opero/tests/timesheet_client.test.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const moment = require("../../../frappe/node_modules/moment");

function loadForm(allocationBalances = []) {
	const handlers = [];
	const rows = new Map();
	const dashboardSections = [];
	const frappe = {
		ui: { form: { on: (doctype, events) => handlers.push({ doctype, events }) } },
		utils: { debounce: (fn) => fn, escape_html: (value) => String(value || "") },
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
		xcall: async (method) =>
			method === "opero.api.timesheet.get_allocation_balances" ? allocationBalances : 0,
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
		refresh_field() {},
		dirty() {},
		set_value: async () => {},
		is_new: () => true,
	};
	return { handlers, rows, frm, buttons, hiddenFields, dashboardSections };
}

test("Timesheet hides report-only and unused fields on the form", async () => {
	const { handlers, frm, hiddenFields } = loadForm();
	for (const { doctype, events } of handlers)
		if (doctype === "Timesheet" && events.refresh) await events.refresh(frm);
	assert.equal(hiddenFields.has("employee_name"), true);
	assert.equal(hiddenFields.has("workflow_state"), true);
	assert.equal(hiddenFields.has("connections_tab"), true);
});

test("allocation summary uses concise labels", async () => {
	const { handlers, frm, dashboardSections } = loadForm([
		{ task: "TASK-1", task_name: "Design", month: "Sep 2026", allocated: 10, submitted: 3, current: 2, remaining: 5 },
	]);
	Object.assign(frm.doc, { employee: "EMP-1", parent_project: "PROJ-1" });
	const handler = handlers.find(
		({ doctype, events }) =>
			doctype === "Timesheet" && String(events.refresh).includes("get_allocation_balances")
	);

	await handler.events.refresh(frm);

	assert.equal(dashboardSections.length, 1);
	const [html, title] = dashboardSections[0];
	assert.equal(title, "Allocations");
	for (const heading of ["Task / Month", "Allocated", "Submitted", "This sheet", "Remaining"]) {
		assert.match(html, new RegExp(`<th>${heading}</th>`));
	}
	assert.doesNotMatch(html, /Remaining after this timesheet|This timesheet/);
});

for (const [start, hours] of [
	["2026-01-31 23:00:00", 3],
	["2026-01-31 23:00:00", 50],
]) {
	test(`split preserves timestamps and ${hours} hours across midnight`, async () => {
		const { handlers, rows, frm, buttons } = loadForm();
		const row = {
			doctype: "Timesheet Detail",
			name: "original",
			from_time: start,
			hours,
			task: "task",
			project: "project",
			description: "Work",
			is_billable: 1,
			activity_type: "rate",
			zoho_entry_id: "remote",
			custom_zoho_sync_uncertain: 1,
			custom_week_of_month: "Week 5",
		};
		frm.doc.time_logs.push(row);
		rows.set(row.name, row);
		for (const { doctype, events } of handlers)
			if (doctype === "Timesheet" && events.refresh) await events.refresh(frm);
		await buttons.get("Split at midnight")();
		assert.equal(frm.doc.time_logs[0].from_time, start);
		assert.equal(
			frm.doc.time_logs.reduce((sum, entry) => sum + entry.hours, 0),
			hours
		);
		const last = frm.doc.time_logs.at(-1);
		assert.equal(
			last.to_time,
			moment(start).add(hours, "hours").format("YYYY-MM-DD HH:mm:ss")
		);
		for (let i = 1; i < frm.doc.time_logs.length; i++) {
			const entry = frm.doc.time_logs[i];
			assert.equal(entry.from_time, frm.doc.time_logs[i - 1].to_time);
			assert.equal(entry.activity_type, "rate");
			assert.equal(entry.description, "Work");
			assert.equal(entry.zoho_entry_id, undefined);
			assert.equal(entry.custom_zoho_sync_uncertain, undefined);
			assert.equal(
				entry.custom_week_of_month,
				"Week " +
					(Math.floor(
						(moment(entry.from_time).date() -
							1 +
							moment(entry.from_time).startOf("month").isoWeekday() -
							1) /
							7
					) +
						1)
			);
		}
	});
}

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
