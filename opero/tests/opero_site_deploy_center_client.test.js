// Run with: node opero/tests/opero_site_deploy_center_client.test.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

test("recent deploys display a relative timestamp", () => {
	let events;
	const frappe = {
		datetime: {
			comment_when: (value) => `<span title="18-09-2026 14:00">2 hours ago:${value}</span>`,
		},
		ui: { form: { on: (doctype, handlers) => (events = handlers) } },
		user_info: () => ({ fullname: "Administrator" }),
		utils: { escape_html: (value) => String(value || "") },
	};
	const context = {
		frappe,
		$: () => ({}),
		__: (text, values = []) => values.reduce((result, value, index) => result.replace(`{${index}}`, value), text),
	};
	vm.createContext(context);
	vm.runInContext(
		fs.readFileSync(path.join(__dirname, "../public/js/opero_site_deploy_center.js"), "utf8"),
		context
	);

	let html = "";
	const frm = {
		disable_save() {},
		doc: {
			deploy_log: [
				{
					deployed_on: "2026-09-18 14:00:00",
					deployed_by: "Administrator",
					file_count: 2,
					sha: "1234567890",
					commit_url: "https://example.com/commit/1234567890",
				},
			],
		},
		get_field: () => ({ $wrapper: { html: (value) => (html = value) } }),
		has_perm: () => false,
	};

	events.refresh(frm);

	assert.match(html, />2 hours ago:2026-09-18 14:00:00<\/span>/);
	assert.match(html, /title="18-09-2026 14:00"/);
});
