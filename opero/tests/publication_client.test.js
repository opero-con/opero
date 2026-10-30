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

test("choosing Product clears the date", () => {
	const { events, frm } = loadForm(1);
	const values = [];
	frm.doc = { publication_type: "Product", published_on: "2026-10-15", year: 2026 };
	frm.set_value = (field, value) => values.push([field, value]);
	events.publication_type(frm);
	assert.deepEqual(values, [
		["published_on", ""],
		["year", ""],
	]);
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

function pdfField() {
	const nodes = [];
	return {
		nodes,
		find(selector) {
			const className = selector.slice(1);
			const matches = nodes.filter((node) => node.className === className && !node.removed);
			return {
				remove() {
					for (const node of matches) node.removed = true;
				},
			};
		},
		append(node) {
			nodes.push(node);
			return this;
		},
	};
}

function loadRename(doc) {
	const handlers = {};
	const wrapper = pdfField();
	const calls = [];
	const prompts = [];
	const messages = [];
	vm.runInNewContext(
		fs.readFileSync(
			path.join(__dirname, "../opero_site/doctype/publication/publication.js"),
			"utf8"
		),
		{
			frappe: {
				ui: { form: { on: (_, value) => Object.assign(handlers, value) } },
				prompt: (...args) => prompts.push(args),
				call: (args) => calls.push(args),
				msgprint: (message) => messages.push(message),
			},
			$: (tag, attributes = {}) => ({
				tag,
				className: attributes.class,
				text: attributes.text,
				children: [],
				events: {},
				append(child) {
					this.children.push(child);
					return this;
				},
				on(event, handler) {
					this.events[event] = handler;
					return this;
				},
			}),
			__: (value) => value,
		}
	);
	const frm = {
		doc,
		is_dirty: () => false,
		reload_doc() {},
		get_field: (name) => (name === "file_url" ? { $wrapper: wrapper } : null),
	};
	handlers.refresh(frm);
	const row = wrapper.nodes.find((node) => node.className === "pdf-rename" && !node.removed);
	return { frm, row, button: row && row.children[0], prompts, calls, messages };
}

test("rename is offered for a PDF uploaded on the publication", () => {
	const loaded = loadRename({
		name: "PUB-00002",
		file_url: "/private/files/ugly%20name.pdf",
	});
	assert.equal(loaded.button.text, "Rename");
	loaded.button.events.click();
	const [field, submit, title, primary] = loaded.prompts[0];
	assert.equal(title, "Rename PDF");
	assert.equal(primary, "Rename");
	assert.equal(field.default, "ugly name.pdf");
	assert.equal(field.description, "The public page uses this name after the next deploy.");
	let reloaded = false;
	loaded.frm.reload_doc = () => {
		reloaded = true;
	};
	submit({ filename: "Annual report.pdf" });
	assert.equal(
		loaded.calls[0].method,
		"opero.opero_site.doctype.publication.publication.rename_publication_pdf"
	);
	assert.equal(loaded.calls[0].args.name, "PUB-00002");
	assert.equal(loaded.calls[0].args.filename, "Annual report.pdf");
	loaded.calls[0].callback();
	assert.equal(reloaded, true);
});

test("rename waits until the publication is saved", () => {
	for (const doc of [
		{ name: "PUB-00002", file_url: "https://example.com/report.pdf" },
		{ name: "PUB-00002", file_url: "/downloads/report.pdf" },
		{ name: "PUB-00002", file_url: "/private/files/report.pdf", __islocal: 1 },
		{ name: "PUB-00002", file_url: "" },
	]) {
		assert.equal(loadRename(doc).row, undefined);
	}
	const loaded = loadRename({
		name: "PUB-00002",
		file_url: "/files/report.pdf",
	});
	loaded.frm.is_dirty = () => true;
	loaded.button.events.click();
	assert.deepEqual(loaded.messages, ["Save the publication before renaming its PDF."]);
	assert.equal(loaded.prompts.length, 0);
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

test("publication format reveals the chosen fields and preserves existing destinations", () => {
	let render;
	function element() {
		return {
			value: "",
			empty() {
				return this;
			},
			append() {
				return this;
			},
			val(value) {
				if (value === undefined) return this.value;
				this.value = value;
				return this;
			},
			on(_, fn) {
				this.change = fn;
				return this;
			},
		};
	}
	let select;
	const context = {
		frappe: { ui: { form: { on() {} } } },
		__: (value) => value,
		$: (tag) => {
			const node = element();
			if (tag === "<select>") select = node;
			return node;
		},
	};
	vm.createContext(context);
	vm.runInContext(
		fs.readFileSync(
			path.join(__dirname, "../opero_site/doctype/publication/publication.js"),
			"utf8"
		),
		context
	);
	render = context.show_publication_source;
	const visible = {};
	const frm = {
		doc: {},
		get_field: () => ({ $wrapper: element() }),
		toggle_display: (field, value) => (visible[field] = value),
	};
	render(frm);
	assert.equal(select.val(), "pdf");
	assert.equal(visible.file_url, true);
	assert.equal(visible.external_url, false);
	select.val("webpage").change();
	assert.equal(visible.file_url, false);
	assert.equal(visible.external_url, true);
	frm.doc.file_url = "/private/files/report.pdf";
	select.change();
	assert.equal(visible.file_url, true);
	assert.equal(frm.doc.file_url, "/private/files/report.pdf");
	frm.doc.external_url = "https://example.com";
	render(frm);
	assert.equal(select.val(), "both");
	assert.equal(visible.external_url, true);
});
