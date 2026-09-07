frappe.ui.form.on("Contact", {
	setup(frm) {
		frm.set_query("custom_mailing_lists", () => ({ query: "opero.mailing.membership.search_lists" }));
	},
	refresh(frm) {
		frm.fields_dict.custom_mailing_status?.$wrapper.html(opero.mailing.status_html(frm.doc.custom_mailing_lists || []));
		if (!frm.is_new() && opero.mailing.is_manager()) {
			frm.add_custom_button(__("Review confirmation requests"), () => {
				if (frm.is_dirty()) return frappe.msgprint(__("Save the Contact before reviewing recipients."));
				opero.mailing.review({ contacts: [frm.doc.name] }, () => frm.reload_doc());
			}, __("Mailing Lists"));
		}
	},
	after_save(frm) { frm.trigger("refresh"); },
});
