// Run with: node --test opero/tests/publication_client.test.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

const LINE = 20;
const PADDING = 12;

function loadForm(lines) {
	const handlers = new Map();
	const listeners = [];
	const data = {};
	const input = { rows: 3, style: {}, scrollHeight: lines * LINE + PADDING };
	const $input = {
		data: (key, value) => (value === undefined ? data[key] : (data[key] = value)),
		on: (event, handler) => listeners.push([event, handler]),
		get: () => input,
	};
	const context = {
		frappe: { ui: { form: { on: (doctype, events) => handlers.set(doctype, events) } } },
		getComputedStyle: () => ({ lineHeight: `${LINE}px` }),
	};
	vm.createContext(context);
	vm.runInContext(
		fs.readFileSync(path.join(__dirname, "../opero_site/doctype/publication/publication.js"), "utf8"),
		context
	);
	const frm = { get_field: (name) => (name === "summary" ? { $input } : null) };
	return { events: handlers.get("Publication"), frm, input, listeners };
}

test("an empty summary shows two lines", () => {
	const { events, frm, input } = loadForm(1);
	events.refresh(frm);
	assert.equal(input.rows, 1);
	assert.equal(input.style.height, `${2 * LINE + PADDING}px`);
	assert.equal(input.style.overflowY, "hidden");
});

test("the summary keeps one spare line below the text", () => {
	const { events, frm, input } = loadForm(4);
	events.summary(frm);
	assert.equal(input.style.height, `${5 * LINE + PADDING}px`);
});

test("refresh binds the input listener once", () => {
	const { events, frm, listeners } = loadForm(1);
	events.refresh(frm);
	events.refresh(frm);
	assert.deepEqual(listeners.map(([event]) => event), ["input"]);
});
