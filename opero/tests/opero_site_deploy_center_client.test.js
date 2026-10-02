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

function loadDeployCenter(frappeOverrides = {}) {
	const frappe = {
		ui: { form: { on: () => {} } },
		utils: { escape_html: (value) => String(value || "") },
		...frappeOverrides,
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
	return context;
}

test("only website content files offer Load from website", () => {
	const { pendingRowHtml } = loadDeployCenter();

	assert.match(
		pendingRowHtml({ action: "update", path: "content/privacy/privacy.md", title: "Privacy policy" }),
		/class="small opero-pending-load" data-path="content\/privacy\/privacy.md"/
	);
	assert.doesNotMatch(
		pendingRowHtml({ action: "update", path: "media/homepage/hero.jpg", title: "hero.jpg" }),
		/opero-pending-load/
	);
});

test("loading one file removes only that row", () => {
	const calls = [];
	const alerts = [];
	const context = loadDeployCenter({
		confirm: (message, yes) => yes(),
		call: (options) => {
			calls.push(options);
			options.callback({ message: { message: "Loaded Privacy policy from the website." } });
		},
		show_alert: (options) => alerts.push(options),
	});
	let html = "";
	const frm = {
		page: {},
		_opero_pending_files: [
			{ action: "update", path: "content/privacy/privacy.md", title: "Privacy policy" },
			{ action: "update", path: "content/team/anita.md", title: "Anita", group: "Team" },
		],
		get_field: () => ({ $wrapper: { html: (value) => (html = value), find: () => ({ on() {} }) } }),
	};

	context.loadFileFromWebsite(frm, "content/privacy/privacy.md", "Privacy policy");

	assert.equal(calls[0].method, "opero.opero_site.load.load_file_from_website");
	assert.equal(calls[0].args.path, "content/privacy/privacy.md");
	assert.equal(frm._opero_pending_files.map((row) => row.path).join(), "content/team/anita.md");
	assert.doesNotMatch(html, /Privacy policy/);
	assert.match(html, /Anita/);
	assert.equal(alerts[0].message, "Loaded Privacy policy from the website.");
});

function pendingForm(files, selected = []) {
	let html = "";
	const frm = {
		page: {},
		_opero_selected: new Set(selected),
		get_field: () => ({ $wrapper: { html: (value) => (html = value), find: () => ({ on() {} }) } }),
	};
	return { frm, files, html: () => html };
}

test("pending rows start unchecked and keep a selection that is still pending", () => {
	const { renderPending } = loadDeployCenter();
	const rows = [
		{ action: "update", path: "content/publications/finished.md", title: "Finished", group: "Publications" },
		{ action: "update", path: "content/publications/trainee.md", title: "Trainee", group: "Publications" },
	];
	const form = pendingForm(rows, ["content/publications/finished.md", "content/publications/gone.md"]);

	renderPending(form.frm, form.frm.get_field().$wrapper, { files: rows });

	assert.match(form.html(), /data-path="content\/publications\/finished.md" checked>/);
	assert.match(form.html(), /data-path="content\/publications\/trainee.md">/);
	assert.deepEqual([...form.frm._opero_selected], ["content/publications/finished.md"]);
});

test("Deploy selected asks for a selection before calling the server", () => {
	const calls = [];
	const messages = [];
	const context = loadDeployCenter({ call: (options) => calls.push(options), msgprint: (text) => messages.push(text) });

	context.reviewSelectedDeploy({ _opero_selected: new Set() });

	assert.equal(calls.length, 0);
	assert.match(messages[0], /Select the changes to deploy/);
});

test("Deploy selected reviews the server's paths and deploys exactly those", () => {
	const calls = [];
	const confirms = [];
	const context = loadDeployCenter({
		call: (options) => {
			calls.push(options);
			if (options.method.endsWith("preview_selected_deploy")) {
				options.callback({
					message: {
						paths: ["content/partners/new.md", "content/partners/old.md"],
						files: [
							{ action: "update", path: "content/partners/new.md", title: "New Name" },
							{ action: "delete", path: "content/partners/old.md", title: "Old Name" },
						],
					},
				});
			}
		},
		confirm: (message, yes) => {
			confirms.push(message);
			yes();
		},
	});
	const form = pendingForm([], ["content/partners/new.md"]);
	form.frm.page = {};

	context.reviewSelectedDeploy(form.frm);

	assert.deepEqual([...calls[0].args.paths], ["content/partners/new.md"]);
	assert.match(confirms[0], /Unselected changes stay queued/);
	assert.match(confirms[0], /<li>Update: New Name<\/li><li>Remove: Old Name<\/li>/);
	assert.equal(calls[1].method, "opero.opero_site.publish.deploy_selected");
	assert.deepEqual(calls[1].args.paths, ["content/partners/new.md", "content/partners/old.md"]);
});
