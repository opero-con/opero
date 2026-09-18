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
	return { handlers, singleValueCalls };
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
	const { handlers, singleValueCalls } = loadPublishStatus("To deploy");
	const sections = ["Hero", "About", "Our Work", "Impact", "Partners"];

	for (const doctype of sections) {
		const { frm, messages } = makeForm(doctype);
		await handlers.get(doctype).refresh(frm);

		assert.equal(messages.length, 2);
		assert.match(messages[1][0], /This Home Page is queued for the next website deploy/);
		assert.equal(messages[1][1], "blue");
	}
	assert.deepEqual(singleValueCalls, sections.map(() => ["Home Page", "status"]));
});

test("every directly deployable DocType displays its own pending ribbon", async () => {
	const { handlers } = loadPublishStatus("Published");
	const doctypes = [
		["Publication", { status: "To deploy" }],
		["Employee", { website_status: "To deploy" }],
		["Enterprise", { website_status: "To deploy" }],
		["Home Page", { status: "To deploy" }],
		["Privacy policy", { status: "To deploy" }],
		["Site Settings", { status: "To deploy" }],
	];

	for (const [doctype, doc] of doctypes) {
		const { frm, messages } = makeForm(doctype, doc);
		await handlers.get(doctype).refresh(frm);

		assert.equal(messages.length, 2);
		assert.match(messages[1][0], new RegExp(`This ${doctype} is queued for the next website deploy`));
		assert.equal(messages[1][1], "blue");
	}
});
