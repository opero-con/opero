frappe.ui.form.on("Email Group", {
	refresh(frm) {
		if (frm.is_new() || !opero.mailing.is_manager()) return;
		frm.add_custom_button(__("View members"), () => {
			frappe.set_route("List", "Email Group Member", { email_group: frm.doc.name });
		}, __("Action"));
		frm.add_custom_button(__("Add Contacts"), () => {
			frappe.prompt({ fieldname: "contacts", fieldtype: "MultiSelectList", label: __("Contacts"), reqd: 1,
				get_data: (txt) => frappe.db.get_link_options("Contact", txt) }, async (values) => {
				await frappe.call({ method: "opero.mailing.membership.bulk_membership",
					args: { contacts: values.contacts, mailing_lists: [frm.doc.name], action: "add" }, freeze: true });
				frm.reload_doc();
				frappe.show_alert(__("Memberships saved. No emails were sent."));
			}, __("Add Contacts"), __("Add"));
		}, __("Action"));
	},
});
