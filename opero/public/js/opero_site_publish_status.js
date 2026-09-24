const OPTIONAL_SITE_DOCTYPES = ["Publication", "Employee", "Enterprise", "Partner"];
const ALWAYS_ON_SITE_DOCTYPES = ["Home Page", "Privacy policy", "Site Settings"];
const HOME_PAGE_SECTION_DOCTYPES = ["Hero", "About", "Our Work", "Impact"];
const SITE_CONTENT_DOCTYPES = OPTIONAL_SITE_DOCTYPES.concat(ALWAYS_ON_SITE_DOCTYPES);
// Enterprise CRM Status stays on the Details tab; do not drive the form/list indicator.
const INDICATOR_SITE_DOCTYPES = SITE_CONTENT_DOCTYPES.filter((name) => name !== "Enterprise");
const PUBLISH_STATUS_FIELD = {
	Enterprise: "website_status",
	Employee: "website_status",
	Partner: "website_status",
};
const LIVE_STATUSES = ["To update", "Published", "To unpublish"];
const QUEUED_STATUSES = ["To publish", "To update", "To unpublish"];
const STATUS_COLORS = {
	Draft: "gray",
	"To publish": "blue",
	"To update": "blue",
	Published: "green",
	"To unpublish": "orange",
};

if (!window._opero_publish_status_bound) {
	window._opero_publish_status_bound = true;
	SITE_CONTENT_DOCTYPES.forEach(bindPublishStatus);
	HOME_PAGE_SECTION_DOCTYPES.forEach(bindHomePageStatus);
}

function setupStatusPills() {
	frappe.provide("frappe.listview_settings");
	INDICATOR_SITE_DOCTYPES.forEach(bindStatusPill);
	if (typeof frappe.get_indicator === "function" && !frappe.get_indicator._opero_wrapped) {
		wrapGetIndicator();
	}
}

setupStatusPills();
$(document).on("app_ready", setupStatusPills);

function publishStatusField(doctype) {
	return PUBLISH_STATUS_FIELD[doctype] || "status";
}

function wrapGetIndicator() {
	const original = frappe.get_indicator;
	const wrapped = function (doc, doctype, show_workflow_state) {
		if (doc && doc.__unsaved) {
			return original.call(this, doc, doctype, show_workflow_state);
		}
		const name = doctype || (doc && doc.doctype);
		if (doc && INDICATOR_SITE_DOCTYPES.includes(name)) {
			const mapped = getPublishStatusIndicator(doc, name);
			if (mapped) {
				return mapped;
			}
		}
		return original.call(this, doc, doctype, show_workflow_state);
	};
	wrapped._opero_wrapped = true;
	frappe.get_indicator = wrapped;
}

function bindPublishStatus(doctype) {
	const field = publishStatusField(doctype);
	const handlers = {
		refresh(frm) {
			if (!frm.is_dirty()) {
				frm._saved_publish_status = frm.doc[field];
			}
			if (INDICATOR_SITE_DOCTYPES.includes(doctype)) {
				setPublishStatusPill(frm);
			}
			setDeployRibbon(frm);
		},
	};
	if (OPTIONAL_SITE_DOCTYPES.includes(doctype)) {
		handlers.show_on_website = function (frm) {
			if (frm._syncing_publish_status) {
				return;
			}
			frm._syncing_publish_status = true;
			const saved = frm._saved_publish_status || frm.doc[field];
			frm.doc[field] = statusFromCheckbox(frm.doc.show_on_website, saved);
			frm.refresh_field(field);
			frm._syncing_publish_status = false;
			if (INDICATOR_SITE_DOCTYPES.includes(doctype)) {
				setPublishStatusPill(frm);
			}
			setDeployRibbon(frm);
		};
	}
	frappe.ui.form.on(doctype, handlers);
}

function bindHomePageStatus(doctype) {
	frappe.ui.form.on(doctype, {
		async refresh(frm) {
			const status = await frappe.db.get_single_value("Home Page", "status");
			setDeployRibbon(frm, status);
		},
	});
}

function statusFromCheckbox(publish, status) {
	const is_live = LIVE_STATUSES.includes(status);
	if (cint(publish)) {
		return is_live ? "To update" : "To publish";
	}
	return is_live ? "To unpublish" : "Draft";
}

function setPublishStatusPill(frm) {
	if (!frm.page) {
		return;
	}
	const indicator = getPublishStatusIndicator(frm.doc, frm.doctype);
	if (indicator) {
		frm.page.set_indicator(indicator[0], indicator[1]);
	}
}

function setDeployRibbon(frm, status = frm.doc[publishStatusField(frm.doctype)]) {
	if (!frm.layout) {
		return;
	}
	frm.layout.show_message();
	if (!QUEUED_STATUSES.includes(status)) {
		return;
	}
	const link = frappe.utils.get_form_link(
		"Deploy Center",
		"Deploy Center",
		true,
		__("Deploy Center")
	);
	const text =
		status === "To unpublish"
			? __("Will be removed on the next deploy. {0}", [link])
			: __("Will be published on the next deploy. {0}", [link]);
	frm.layout.show_message(`<span>${text}</span>`, STATUS_COLORS[status], true);
}

function bindStatusPill(doctype) {
	frappe.provide("frappe.listview_settings");
	const settings = frappe.listview_settings[doctype] || {};
	settings.get_indicator = (doc) => getPublishStatusIndicator(doc, doctype);
	frappe.listview_settings[doctype] = settings;
}

function getPublishStatusIndicator(doc, doctype) {
	const field = publishStatusField(doctype || doc.doctype);
	const status = doc[field];
	if (STATUS_COLORS[status]) {
		return [__(status), STATUS_COLORS[status], `${field},=,${status}`];
	}
}
