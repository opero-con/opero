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
		fs.readFileSync(
			path.join(__dirname, "../opero_site/doctype/publication/publication.js"),
			"utf8"
		),
		context
	);
	const frm = { get_field: (name) => (name === "summary" ? { $input } : null) };
	return { events: handlers.get("Publication"), frm, input, listeners };
}

test("URL is labeled and shown only after a saved publication has a slug", () => {
	const { frm } = loadForm(1);
	let link;
	let visible;
	let label;
	const wrapper = {
		empty() {
			link = null;
			label = null;
			return this;
		},
		append(value) {
			if (value.tag === "<a>") link = value;
			else label = value;
			return this;
		},
	};
	const handlers = {};
	vm.runInNewContext(
		fs.readFileSync(
			path.join(__dirname, "../opero_site/doctype/publication/publication.js"),
			"utf8"
		),
		{
			frappe: { ui: { form: { on: (_, value) => Object.assign(handlers, value) } } },
			$: (tag, attributes) => ({ tag, ...attributes }),
			__: (value) => value,
		}
	);
	frm.get_field = (name) => (name === "website_link" ? { $wrapper: wrapper } : null);
	frm.toggle_display = (_, value) => (visible = value);
	for (const doc of [
		...["Published", "To update", "To unpublish", "Draft", "To publish"].map((status) => ({
			status,
			slug: "annual-report",
		})),
		{ status: "Draft", slug: "" },
		{ status: "Draft", slug: "annual-report", __islocal: 1 },
	]) {
		frm.doc = doc;
		handlers.refresh(frm);
		const has_url = !!doc.slug && !doc.__islocal;
		assert.equal(visible, has_url);
		if (has_url) {
			assert.equal(label.text, "URL");
			assert.equal(link.href, "https://opero-services.com/publications/annual-report.html");
			assert.equal(link.text, "opero-services.com/publications/annual-report");
			assert.equal(link.rel, "noopener noreferrer");
		} else {
			assert.equal(link, null);
			assert.equal(label, null);
		}
	}
});

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
	assert.deepEqual(
		listeners.map(([event]) => event),
		["input"]
	);
});
