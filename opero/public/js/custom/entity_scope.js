// Opero: entity scoping in the form.
//
// The server is the authority — `opero/entity.py` re-derives the company from
// the project on every save and refuses anything that disagrees. This file only
// makes that visible while typing: the company follows the project immediately,
// the field is locked once a project is chosen, and link pickers stop offering
// records that belong to the other entity.

frappe.provide("opero.entity");

// Mirrors PROJECT_SCOPED_DOCTYPES in opero/entity.py.
opero.entity.SCOPED = {
	Task: { project: "project", company: "company" },
	Timesheet: { project: "parent_project", company: "company" },
	"Travel Request": { project: "custom_project", company: "company" },
	"Expense Claim": { project: "project", company: "company" },
	"Material Request": { project: "custom_project", company: "company" },
	"Activity Type": { project: "custom_project", company: "custom_company" },
	"Budget Line": { project: "project", company: "company" },
	"Cash Advance-Reimbursable Form": { project: "project", company: "company" },
	"Consultant Task": { project: "project", company: "company" },
	"Project Budget": { project: "project", company: "company" },
	"Project Time Allocation": { project: "project", company: "company" },
	"Task Time Distribution": { project: "project", company: "company" },
};

// Link fields that must not reach outside the document's entity.
// `by` is either "company" (the entity itself) or "project".
opero.entity.LINK_FILTERS = {
	Task: [{ field: "parent_task", by: "project" }],
	Timesheet: [
		{ table: "time_logs", field: "project", by: "company" },
		{ table: "time_logs", field: "task", by: "project" },
		{ table: "time_logs", field: "activity_type", by: "company", target: "custom_company" },
	],
	"Expense Claim": [{ table: "expenses", field: "project", by: "company" }],
	"Project Budget": [{ table: "budget_items", field: "account", by: "company" }],
	"Project Time Allocation": [
		{ table: "time_allocation_detail", field: "project_task", by: "project" },
	],
	"Task Time Distribution": [{ field: "project_task", by: "project" }],
};

opero.entity.lock_company = function (frm, scope) {
	const field = frm.get_field(scope.company);
	if (!field) return;
	frm.set_df_property(scope.company, "read_only", frm.doc[scope.project] ? 1 : 0);
};

// Entity descriptions are stable for a session, so each one is fetched once.
// The promise itself is cached, which also collapses concurrent lookups.
opero.entity._described = {};

opero.entity.describe = function (company) {
	if (!company) return Promise.resolve(null);
	if (!opero.entity._described[company]) {
		opero.entity._described[company] = frappe.xcall("opero.entity.get_company_entity", {
			company,
		});
	}
	return opero.entity._described[company];
};

opero.entity.follow_project = async function (frm, scope) {
	const project = frm.doc[scope.project];
	if (!project) return;

	const entity = await frappe.xcall("opero.entity.get_project_entity", { project });
	if (!entity || !entity.company) return;
	opero.entity._described[entity.company] = Promise.resolve(entity);

	const previous = frm.doc[scope.company];
	if (previous !== entity.company) {
		// Set it here rather than waiting for the save, so company-dependent
		// fields (accounts, cost centres, currency) refresh against the right
		// entity while the user is still filling the form in.
		await frm.set_value(scope.company, entity.company);

		// Announced only on the change itself. Choosing a project can move a
		// document — and its currency — into another entity's books, and that
		// is a moment rather than a state, so a standing banner would look
		// identical either side of it.
		if (previous) {
			frappe.show_alert({
				message: __("Moved to {0} ({1})", [entity.label, entity.currency || ""]),
				indicator: "orange",
			});
		}
	}

	opero.entity.lock_company(frm, scope);
	opero.entity.flag_cross_entity(frm, scope);
};

// A headline only when the document belongs to an entity other than the user's
// own. That is the surprising case; saying so on every document would make it
// furniture nobody reads.
opero.entity.flag_cross_entity = async function (frm, scope) {
	const company = frm.doc[scope.company];
	const home = frappe.boot.opero_home_company;

	// Cleared first: a headline set for one document would otherwise survive
	// into the next one rendered by the same form.
	frm.dashboard.clear_headline();

	if (!company || !home || company === home) return;

	const entity = await opero.entity.describe(company);
	const label = (entity && entity.label) || company;

	// The form may have moved on while the description was in flight.
	if (frm.doc[scope.company] !== company) return;

	frm.dashboard.set_headline(
		__("Cross-entity: this belongs to {0}, which carries the cost — not your own entity.", [
			frappe.utils.escape_html(label),
		]),
		"orange"
	);
};

opero.entity.apply_link_filters = function (frm, scope) {
	const rules = opero.entity.LINK_FILTERS[frm.doctype] || [];

	for (const rule of rules) {
		const build_filters = () => {
			if (rule.by === "project") {
				return frm.doc[scope.project] ? { project: frm.doc[scope.project] } : {};
			}
			const value = frm.doc[scope.company];
			if (!value) return {};
			return { [rule.target || "company"]: value };
		};

		const query = () => ({ filters: build_filters() });

		if (rule.table) {
			frm.set_query(rule.field, rule.table, query);
		} else {
			frm.set_query(rule.field, query);
		}
	}
};

Object.entries(opero.entity.SCOPED).forEach(([doctype, scope]) => {
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			opero.entity.lock_company(frm, scope);
			opero.entity.apply_link_filters(frm, scope);
			opero.entity.flag_cross_entity(frm, scope);
		},
		[scope.project](frm) {
			opero.entity.follow_project(frm, scope);
		},
	});
});
