// Run with: node --test opero/tests/entity_scope_client.test.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

const LABELS = { "Opero Services": "Opero Services", NGC: "Nicola Greene Consulting" };

function loadEntityScope(session) {
	const context = {
		frappe: {
			boot: { opero_session_entity: session },
			provide: () => {},
			ui: { form: { on: () => {} } },
			utils: { escape_html: (value) => String(value).replace(/</g, "&lt;") },
			xcall: async (_method, { company }) => ({
				company,
				label: LABELS[company] || company,
			}),
		},
		opero: { entity: {} },
		__: (text, args = []) => text.replace(/\{(\d+)\}/g, (_match, index) => args[index]),
	};
	vm.createContext(context);
	vm.runInContext(
		fs.readFileSync(path.join(__dirname, "../public/js/custom/entity_scope.js"), "utf8"),
		context
	);
	return context.opero.entity;
}

function makeForm(company) {
	return {
		doctype: "Timesheet",
		doc: { company },
		headline: null,
		dashboard: {
			clear_headline() {
				this.form.headline = null;
			},
			set_headline(message) {
				this.form.headline = message;
			},
		},
	};
}

async function headlineFor(session, company) {
	const entity = loadEntityScope(session);
	const frm = makeForm(company);
	frm.dashboard.form = frm;
	frm.headline = "left over from the previous document";
	await entity.flag_cross_entity(frm, { company: "company", project: "parent_project" });
	return frm.headline;
}

test("names both entities when the document is outside the session's entity", async () => {
	const session = { company: "Opero Services", label: "Opero Services" };
	assert.equal(
		await headlineFor(session, "NGC"),
		"Timesheet belongs to <b>Nicola Greene Consulting</b> while your session is in <b>Opero Services</b>"
	);
});

test("stays quiet when the document is in the session's entity", async () => {
	const session = { company: "NGC", label: "Nicola Greene Consulting" };
	assert.equal(await headlineFor(session, "NGC"), null);
});

test("stays quiet without a session entity or a document company", async () => {
	assert.equal(await headlineFor({}, "NGC"), null);
	assert.equal(await headlineFor(undefined, "NGC"), null);
	assert.equal(await headlineFor({ company: "Opero Services" }, ""), null);
});

test("escapes entity labels", async () => {
	const session = { company: "Opero Services", label: "<i>Opero</i>" };
	assert.match(await headlineFor(session, "NGC"), /session is in <b>&lt;i>Opero&lt;\/i><\/b>$/);
});
