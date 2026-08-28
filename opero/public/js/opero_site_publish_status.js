const SITE_CONTENT_DOCTYPES = [
	"Publication",
	"Team Member",
	"Home Page",
	"Privacy",
	"Site Settings",
];

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
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			setPublishStatusPill(frm);
			setTimeout(() => setPublishStatusPill(frm), 0);
			setTimeout(() => setPublishStatusPill(frm), 50);
		},
		unpublish(frm) {
			if (frm._syncing_publish_status) {
				return;
			}
			frm._syncing_publish_status = true;
			if (cint(frm.doc.unpublish)) {
				frm.set_value("status", "To unpublish");
			} else if (frm.doc.status === "To unpublish") {
				frm.set_value("status", "To publish");
			}
			frm._syncing_publish_status = false;
		},
		status(frm) {
			if (frm._syncing_publish_status) {
				return;
			}
			frm._syncing_publish_status = true;
			frm.set_value("unpublish", frm.doc.status === "To unpublish" ? 1 : 0);
			frm._syncing_publish_status = false;
			setPublishStatusPill(frm);
		},
	});
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
	if (doc.status === "To publish") {
		return [__("Published"), "green", "status,=,To publish"];
	}
	if (doc.status === "To unpublish") {
		return [__("Unpublished"), "gray", "status,=,To unpublish"];
	}
	if (doc.status === "Draft") {
		return [__("Draft"), "orange", "status,=,Draft"];
	}
}
