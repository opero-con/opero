// Run with: node --test opero/tests/timesheet_client.test.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const moment = require("../../../frappe/node_modules/moment");

function loadForm() {
	const handlers = [];
	const rows = new Map();
	const frappe = {
		ui: { form: { on: (doctype, events) => handlers.push({ doctype, events }) } },
		utils: { debounce: (fn) => fn },
		get_meta: () => ({
			fields: [
				"task",
				"project",
				"description",
				"is_billable",
				"activity_type",
				"zoho_entry_id",
				"custom_zoho_sync_uncertain",
			].map((fieldname) => ({ fieldname })),
		}),
		model: {
			set_value: async (doctype, name, values) => Object.assign(rows.get(name), values),
		},
		xcall: async () => 0,
	};
	const context = { frappe, moment, __: (value) => value, document: {}, setTimeout };
	vm.createContext(context);
	vm.runInContext(
		fs.readFileSync(path.join(__dirname, "../public/js/custom/timesheet.js"), "utf8"),
		context
	);
	const buttons = new Map();
	const frm = {
		doc: { docstatus: 0, time_logs: [] },
		dashboard: { parent: { find: () => ({ remove() {} }) } },
		add_custom_button: (label, action) => buttons.set(label, action),
		add_child: (table, values) => {
			const row = { ...values, doctype: "Timesheet Detail", name: "new-" + rows.size };
			frm.doc.time_logs.push(row);
			rows.set(row.name, row);
			return row;
		},
		toggle_display() {},
		refresh_field() {},
		dirty() {},
		set_value: async () => {},
	};
	return { handlers, rows, frm, buttons };
}

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
