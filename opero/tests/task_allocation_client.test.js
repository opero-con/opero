// Run with: node --test opero/tests/task_allocation_client.test.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

function loadForm(capacity) {
	let events;
	let html = "";
	let visible = false;
	let title = "";
	let sections = 0;
	let calls = 0;
	const pending = [];
	const content = {
		length: 0,
		html(value) {
			html = value;
			return this;
		},
		closest() {
			return {
				find() {
					return {
						text(value) {
							title = value;
						},
					};
				},
				toggle(value) {
					visible = value;
				},
			};
		},
	};
	const context = {
		frappe: {
			ui: {
				form: {
					on(_, handlers) {
						events = handlers;
					},
				},
			},
			xcall() {
				calls++;
				if (capacity) return Promise.resolve(capacity);
				return new Promise((resolve) => pending.push(resolve));
			},
			utils: {
				escape_html: (value) =>
					String(value)
						.replaceAll("&", "&amp;")
						.replaceAll("<", "&lt;")
						.replaceAll(">", "&gt;"),
				get_form_link: (_, name, __, label) => `<a href="/app/task/${name}">${label}</a>`,
			},
		},
		flt: (value, digits) => Number(Number(value).toFixed(digits)),
		__: (text, values = []) =>
			values.reduce((result, value, i) => result.replace(`{${i}}`, value), text),
	};
	vm.createContext(context);
	vm.runInContext(
		fs.readFileSync(
			path.join(__dirname, "../opero/doctype/task_allocation/task_allocation.js"),
			"utf8"
		),
		context
	);
	const frm = {
		doc: {
			task: "TASK-1",
			employee: "EMP-1",
			personnel_name: "Person",
			month: "Oct",
			year: "2026",
			hours: 4.9,
			docstatus: 0,
		},
		is_new: () => true,
		dashboard: {
			parent: { find: () => content },
			add_section() {
				sections++;
				content.length = 1;
				return { find: () => content };
			},
			show() {},
		},
	};
	return {
		events,
		frm,
		context,
		pending,
		html: () => html,
		visible: () => visible,
		title: () => title,
		sections: () => sections,
		calls: () => calls,
	};
}
const capacity = {
	task_subject: "Sanitation market assessment",
	budget: { hours: 42.7 },
	task_allocated: 42.7,
	same_task: [{ hours: 2.1 }],
	allocated: 170.7,
	available: 203,
};

test("budget and monthly totals have separate rows with this allocation included once", async () => {
	const form = loadForm(capacity);
	await form.events.employee(form.frm);
	const rows = form.html().match(/<tr><td>.*?<\/tr>/gs);
	assert.equal(rows.length, 2);
	assert.match(rows[0], /Sanitation market assessment.*42\.7h.*42\.7h.*4\.9h over/s);
	assert.match(rows[1], /All - Oct 2026.*203h.*170\.7h.*27\.4h/s);
	assert.match(form.html(), />Task<\/th>/);
	assert.match(form.html(), />Allocations<\/th>/);
	assert.doesNotMatch(form.html(), /Other allocations/);
	assert.doesNotMatch(form.html(), /Budget \/ capacity/);
	assert.match(
		form.html(),
		/>Budget \/ Capacity<\/th>\s*<th class="text-right">Allocations<\/th>/
	);
	assert.equal(form.title(), "Allocations - Person");
	assert.doesNotMatch(form.html(), /This allocation<\/th>/);
	assert.doesNotMatch(form.html(), />Total<\/th>/);
	assert.equal((rows[0].match(/<td/g) || []).length, 4);
	assert.doesNotMatch(form.html(), /This task/);
	assert.doesNotMatch(rows[1], /text-danger/);
});

test("editing hours updates the existing table without another request", async () => {
	const form = loadForm(capacity);
	await form.events.employee(form.frm);
	form.frm.doc.hours = 1;
	form.events.hours(form.frm);
	assert.equal(form.sections(), 1);
	assert.equal(form.calls(), 1);
	assert.match(form.html(), /1h over/);
	assert.match(form.html(), /31\.3h/);
});

test("personnel names update the existing heading without another capacity request", async () => {
	const form = loadForm(capacity);
	await form.events.employee(form.frm);
	form.frm.doc.personnel_name = "Patrick Willy";
	form.events.personnel_name(form.frm);
	assert.equal(form.title(), "Allocations - Patrick Willy");
	assert.equal(form.calls(), 1);
	assert.equal(form.sections(), 1);
});

test("an older response cannot overwrite a changed month", async () => {
	const form = loadForm();
	const first = form.events.employee(form.frm);
	form.frm.doc.month = "Nov";
	const second = form.events.month(form.frm);
	form.pending[1](capacity);
	await second;
	form.pending[0]({ ...capacity, available: 10 });
	await first;
	assert.match(form.html(), /All - Nov 2026/);
	assert.match(form.html(), /203h/);
	assert.equal(form.sections(), 1);
});

test("unknown capacity and missing budgets remain explicit without hiding monthly totals", async () => {
	const form = loadForm({
		...capacity,
		budget: null,
		available: null,
		task_subject: "<script>",
	});
	await form.events.employee(form.frm);
	assert.match(form.html(), /No Hours Budget/);
	assert.doesNotMatch(form.html(), /Monthly capacity is unknown/);
	const monthly_row = form.html().match(/<tr><td>All - Oct 2026.*?<\/tr>/s)[0];
	assert.equal((monthly_row.match(/>—<\/td>/g) || []).length, 2);
	assert.match(form.html(), /Oct 2026/);
	assert.match(form.html(), /&lt;script&gt;/);
	assert.doesNotMatch(form.html(), /<script>/);
});

test("clearing the employee hides the table and invalidates pending requests", async () => {
	const form = loadForm(capacity);
	await form.events.employee(form.frm);
	form.frm.doc.employee = null;
	form.events.employee(form.frm);
	assert.equal(form.visible(), false);
	assert.equal(form.html(), "");
	assert.equal(form.frm.allocation_capacity, null);
});

test("the preview disappears after submission or cancellation without fetching totals", async () => {
	for (const docstatus of [1, 2]) {
		const form = loadForm(capacity);
		await form.events.employee(form.frm);
		assert.equal(form.visible(), true);
		form.frm.doc.docstatus = docstatus;
		form.events.refresh(form.frm);
		assert.equal(form.visible(), false);
		assert.equal(form.html(), "");
		assert.equal(form.calls(), 1);
		form.events.hours(form.frm);
		assert.equal(form.visible(), false);
		assert.equal(form.calls(), 1);
	}
});

test("a pending response cannot restore the preview after submission", async () => {
	const form = loadForm();
	const pending = form.events.employee(form.frm);
	form.frm.doc.docstatus = 1;
	form.events.refresh(form.frm);
	form.pending[0](capacity);
	await pending;
	assert.equal(form.sections(), 0);
	assert.equal(form.visible(), false);
	assert.equal(form.frm.allocation_capacity, null);
});
