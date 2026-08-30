const OPTIONAL_SITE_DOCTYPES = ["Publication", "Team Member"];
const ALWAYS_ON_SITE_DOCTYPES = ["Home Page", "Privacy", "Site Settings"];
const SITE_CONTENT_DOCTYPES = OPTIONAL_SITE_DOCTYPES.concat(ALWAYS_ON_SITE_DOCTYPES);

if (!window._opero_publish_status_bound) {
	window._opero_publish_status_bound = true;
	SITE_CONTENT_DOCTYPES.forEach(bindPublishStatus);
}

function setupStatusPills() {
	frappe.provide("frappe.listview_settings");
	SITE_CONTENT_DOCTYPES.forEach(bindStatusPill);
	if (typeof frappe.get_indicator === "function" && !frappe.get_indicator._opero_wrapped) {
		wrapGetIndicator();
	}
}

setupStatusPills();
$(document).on("app_ready", setupStatusPills);

function wrapGetIndicator() {
	const original = frappe.get_indicator;
	const wrapped = function (doc, doctype, show_workflow_state) {
		if (doc && doc.__unsaved) {
			return original.call(this, doc, doctype, show_workflow_state);
		}
		const name = doctype || (doc && doc.doctype);
		if (doc && SITE_CONTENT_DOCTYPES.includes(name)) {
			const mapped = getPublishStatusIndicator(doc);
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
	const handlers = {
		refresh(frm) {
			if (!frm.is_dirty()) {
				frm._saved_publish_status = frm.doc.status;
			}
			setPublishStatusPill(frm);
		},
	};
	if (OPTIONAL_SITE_DOCTYPES.includes(doctype)) {
		handlers.show_on_website = function (frm) {
			if (frm._syncing_publish_status) {
				return;
			}
			frm._syncing_publish_status = true;
			const saved = frm._saved_publish_status || frm.doc.status;
			frm.doc.status = statusFromCheckbox(frm.doc.show_on_website, saved);
			frm._syncing_publish_status = false;
			setPublishStatusPill(frm);
		};
	}
	frappe.ui.form.on(doctype, handlers);
}

function statusFromCheckbox(show, status) {
	if (cint(show)) {
		return status === "Published" ? "Published" : "To publish";
	}
	if (status === "Unpublished") {
		return "Unpublished";
	}
	if (status === "Published" || status === "To unpublish") {
		return "To unpublish";
	}
	return "Draft";
}

function setPublishStatusPill(frm) {
	if (!frm.page) {
		return;
	}
	const indicator = getPublishStatusIndicator(frm.doc);
	if (indicator) {
		frm.page.set_indicator(indicator[0], indicator[1]);
	}
	if (frm.doctype === "Publication") {
		setPublicationDeployRibbon(frm);
	}
}

function setPublicationDeployRibbon(frm) {
	if (!frm.layout) {
		return;
	}
	frm.layout.show_message();
	if (frm.doc.status !== "To publish" && frm.doc.status !== "To unpublish") {
		return;
	}
	const link = frappe.utils.get_form_link(
		"Deploy Center",
		"Deploy Center",
		true,
		__("Deploy to website")
	);
	const queued_off = frm.doc.status === "To unpublish";
	const text = queued_off
		? __("This publication is queued to come off the website. {0}", [link])
		: __("This publication is queued for the next website deploy. {0}", [link]);
	frm.layout.show_message(`<span>${text}</span>`, queued_off ? "red" : "blue", true);
}

function bindStatusPill(doctype) {
	frappe.provide("frappe.listview_settings");
	const settings = frappe.listview_settings[doctype] || {};
	settings.get_indicator = getPublishStatusIndicator;
	frappe.listview_settings[doctype] = settings;
}

function getPublishStatusIndicator(doc) {
	if (doc.status === "Published") {
		return [__("Published"), "green", "status,=,Published"];
	}
	if (doc.status === "To publish") {
		return [__("To publish"), "blue", "status,=,To publish"];
	}
	if (doc.status === "To unpublish") {
		return [__("To unpublish"), "red", "status,=,To unpublish"];
	}
	if (doc.status === "Unpublished") {
		return [__("Unpublished"), "gray", "status,=,Unpublished"];
	}
	if (doc.status === "Draft") {
		return [__("Draft"), "orange", "status,=,Draft"];
	}
}
