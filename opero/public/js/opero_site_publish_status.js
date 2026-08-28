if (!window._opero_publish_status_bound) {
	window._opero_publish_status_bound = true;
	["Publication", "Team Member", "Home Page", "Privacy", "Site Settings"].forEach(
		bindPublishStatus
	);
}

function bindPublishStatus(doctype) {
	frappe.ui.form.on(doctype, {
		unpublish(frm) {
			if (frm._syncing_publish_status) {
				return;
			}
			frm._syncing_publish_status = true;
			if (cint(frm.doc.unpublish)) {
				frm.set_value("status", "Unpublished");
			} else if (frm.doc.status === "Unpublished") {
				frm.set_value("status", "Published");
			}
			frm._syncing_publish_status = false;
		},
		status(frm) {
			if (frm._syncing_publish_status) {
				return;
			}
			frm._syncing_publish_status = true;
			frm.set_value("unpublish", frm.doc.status === "Unpublished" ? 1 : 0);
			frm._syncing_publish_status = false;
		},
	});
}
