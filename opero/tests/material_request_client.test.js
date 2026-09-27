// Run with: node --test opero/tests/material_request_client.test.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

function loadHandlers() {
	const handlers = [];
	const context = {
		frappe: { ui: { form: { on: (doctype, events) => handlers.push({ doctype, events }) } } },
		flt: (value) => Number(value) || 0,
	};
	vm.createContext(context);
	vm.runInContext(
		fs.readFileSync(path.join(__dirname, "../public/js/custom/material_request.js"), "utf8"),
		context
	);
	return handlers.filter((handler) => handler.doctype === "Material Request Item");
}

test("total updates as quantity, rate or rows change", () => {
	const frm = {
		doc: { items: [{ qty: 2, rate: 10.5 }, { qty: 3, rate: 4 }, { qty: 1 }] },
		set_value(fieldname, value) {
			this.doc[fieldname] = value;
		},
	};
	for (const event of ["qty", "rate", "items_remove"]) {
		frm.doc.custom_total = null;
		const handler = loadHandlers().find((item) => item.events[event]);
		handler.events[event](frm);
		assert.equal(frm.doc.custom_total, 33);
	}
});
