frappe.ui.form.on("Contact", {
	setup(frm) {
		frm.set_query("custom_mailing_lists", () => ({ query: "opero.mailing.membership.search_lists" }));
	},
	refresh(frm) {
		frm.fields_dict.custom_mailing_status?.$wrapper.html(opero.mailing.status_html(frm.doc.custom_mailing_lists || []));
	},
	after_save(frm) { frm.trigger("refresh"); },
});
