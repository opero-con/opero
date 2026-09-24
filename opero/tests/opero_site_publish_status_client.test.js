// Run with: node --test opero/tests/opero_site_publish_status_client.test.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

function loadPublishStatus(status) {
	const handlers = new Map();
	const singleValueCalls = [];
	const frappe = {
		db: {
			get_single_value: async (...args) => {
				singleValueCalls.push(args);
				return status;
			},
		},
		get_indicator() {},
		listview_settings: {},
		provide() {},
		ui: { form: { on: (doctype, events) => handlers.set(doctype, events) } },
		utils: { get_form_link: () => '<a href="/app/deploy-center">Deploy Center</a>' },
	};
	const context = {
		cint: Number,
		document: {},
		frappe,
		window: {},
		$: () => ({ on() {} }),
		__: (text, values = []) => values.reduce((result, value, index) => result.replace(`{${index}}`, value), text),
	};
	vm.createContext(context);
	vm.runInContext(
		fs.readFileSync(path.join(__dirname, "../public/js/opero_site_publish_status.js"), "utf8"),
		context
	);
	return { context, handlers, singleValueCalls };
}

function makeForm(doctype, doc = {}) {
	const messages = [];
	return {
		frm: {
			doctype,
			doc,
			is_dirty: () => false,
			layout: { show_message: (...args) => messages.push(args) },
		},
		messages,
	};
}

test("every homepage section displays the shared Home Page deploy ribbon", async () => {
	const { handlers, singleValueCalls } = loadPublishStatus("To update");
	const sections = ["Hero", "About", "Our Work", "Impact"];

	for (const doctype of sections) {
		const { frm, messages } = makeForm(doctype);
		await handlers.get(doctype).refresh(frm);

		assert.equal(messages.length, 2);
		assert.match(messages[1][0], /Will be published on the next deploy/);
		assert.equal(messages[1][1], "blue");
	}
	assert.deepEqual(singleValueCalls, sections.map(() => ["Home Page", "status"]));
});

test("every site DocType displays its own pending ribbon", async () => {
	const { handlers } = loadPublishStatus("Published");
	const doctypes = [
		["Publication", { status: "To publish" }, /Will be published/, "blue"],
		["Employee", { website_status: "To update" }, /Will be published/, "blue"],
		["Enterprise", { website_status: "To publish" }, /Will be published/, "blue"],
		["Partner", { website_status: "To unpublish" }, /Will be removed/, "orange"],
		["Home Page", { status: "To update" }, /Will be published/, "blue"],
		["Privacy policy", { status: "To update" }, /Will be published/, "blue"],
		["Site Settings", { status: "To update" }, /Will be published/, "blue"],
	];

	for (const [doctype, doc, text, color] of doctypes) {
		const { frm, messages } = makeForm(doctype, doc);
		await handlers.get(doctype).refresh(frm);

		assert.equal(messages.length, 2);
		assert.match(messages[1][0], text);
		assert.equal(messages[1][1], color);
	}
});

test("Draft and Published show no ribbon", async () => {
	const { handlers } = loadPublishStatus("Published");
	for (const status of ["Draft", "Published"]) {
		const { frm, messages } = makeForm("Publication", { status });
		await handlers.get("Publication").refresh(frm);
		assert.equal(messages.length, 1);
	}
});

test("the Publish box follows the status rules", () => {
	const { context } = loadPublishStatus("Published");
	const cases = [
		[1, "Draft", "To publish"],
		[1, "To publish", "To publish"],
		[1, "Published", "To update"],
		[1, "To update", "To update"],
		[1, "To unpublish", "To update"],
		[0, "Draft", "Draft"],
		[0, "To publish", "Draft"],
		[0, "Published", "To unpublish"],
		[0, "To update", "To unpublish"],
		[0, "To unpublish", "To unpublish"],
	];
	for (const [publish, saved, expected] of cases) {
		assert.equal(context.statusFromCheckbox(publish, saved), expected, `${publish} ${saved}`);
	}
});

test("status pills use the agreed colors", () => {
	const { context } = loadPublishStatus("Published");
	const colors = {
		Draft: "gray",
		"To publish": "blue",
		"To update": "blue",
		Published: "green",
		"To unpublish": "orange",
	};
	for (const [status, color] of Object.entries(colors)) {
		const [label, indicator] = context.getPublishStatusIndicator({ website_status: status }, "Partner");
		assert.equal(label, status);
		assert.equal(indicator, color);
	}
});
