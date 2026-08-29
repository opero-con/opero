const SITE_CONTENT_DOCTYPES = [
	"Publication",
	"Team Member",
	"Home Page",
	"Privacy",
	"Site Settings",
];
const USER_STATUS_OPTIONS = ["Draft", "To publish", "To unpublish"];
const PUBLISHER_STATUSES = ["Published", "Unpublished"];

if (!window._opero_publish_status_bound) {
	window._opero_publish_status_bound = true;
	SITE_CONTENT_DOCTYPES.forEach(bindPublishStatus);
	$(document).on("form-refresh", (_event, frm) => {
		if (frm && SITE_CONTENT_DOCTYPES.includes(frm.doctype)) {
			ensureStatusFieldOptions(frm);
		}
	});
}

function setupStatusPills() {
	frappe.provide("frappe.listview_settings");
	restrictBootStatusOptions();
	SITE_CONTENT_DOCTYPES.forEach(bindStatusPill);
	if (typeof frappe.get_indicator === "function" && !frappe.get_indicator._opero_wrapped) {
		wrapGetIndicator();
	}
}

setupStatusPills();
$(document).on("app_ready", setupStatusPills);

function restrictBootStatusOptions() {
	if (typeof frappe === "undefined" || !frappe.meta || !frappe.meta.get_docfield) {
		return;
	}
	SITE_CONTENT_DOCTYPES.forEach((doctype) => {
		const df = frappe.meta.get_docfield(doctype, "status");
		if (df) {
			df.options = USER_STATUS_OPTIONS.join("\n");
		}
	});
}

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
	frappe.ui.form.on(doctype, {
		onload(frm) {
			ensureStatusFieldOptions(frm);
		},
		refresh(frm) {
			ensureStatusFieldOptions(frm);
			hidePublisherStatusChoices(frm);
			setPublishStatusPill(frm);
			setTimeout(() => {
				hidePublisherStatusChoices(frm);
				setPublishStatusPill(frm);
			}, 0);
			setTimeout(() => {
				hidePublisherStatusChoices(frm);
				setPublishStatusPill(frm);
			}, 50);
		},
		unpublish(frm) {
			if (frm._syncing_publish_status) {
				return;
			}
			frm._syncing_publish_status = true;
			if (cint(frm.doc.unpublish)) {
				frm.set_value("status", "To unpublish");
			} else if (frm.doc.status === "To unpublish" || frm.doc.status === "Unpublished") {
				frm.set_value("status", "To publish");
			}
			frm._syncing_publish_status = false;
			ensureStatusFieldOptions(frm);
			hidePublisherStatusChoices(frm);
		},
		status(frm) {
			if (frm._syncing_publish_status) {
				return;
			}
			frm._syncing_publish_status = true;
			frm.set_value(
				"unpublish",
				frm.doc.status === "To unpublish" || frm.doc.status === "Unpublished" ? 1 : 0
			);
			frm._syncing_publish_status = false;
			ensureStatusFieldOptions(frm);
			hidePublisherStatusChoices(frm);
			setPublishStatusPill(frm);
		},
	});
}

function ensureStatusFieldOptions(frm) {
	const field = frm.get_field("status");
	if (!field) {
		return;
	}
	const current = frm.doc.status;
	const options = USER_STATUS_OPTIONS.slice();
	if (PUBLISHER_STATUSES.includes(current)) {
		options.unshift(current);
	}
	const joined = options.join("\n");
	if (field.df.options === joined) {
		return;
	}
	field.df.options = joined;
	field.last_options = null;
	if (field.$input && typeof field.set_options === "function") {
		field.set_options(current);
		field.$input.val(current);
	}
}

function hidePublisherStatusChoices(frm) {
	const field = frm.get_field("status");
	if (!field || !field.$input) {
		return;
	}
	field.$input.find("option").each(function () {
		this.hidden = PUBLISHER_STATUSES.includes(this.value);
	});
	if (frm.doc.status) {
		field.$input.val(frm.doc.status);
	}
}

function setPublishStatusPill(frm) {
	if (!frm.page || frm.doc.__unsaved) {
		return;
	}
	const indicator = getPublishStatusIndicator(frm.doc);
	if (indicator) {
		frm.page.set_indicator(indicator[0], indicator[1]);
	}
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
