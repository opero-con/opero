frappe.ui.form.on("Email Group Member", {
	async custom_contact(frm) {
		const contact = frm.doc.custom_contact;
		frm.set_df_property("email", "read_only", !!contact);
		if (!contact) return;
		await frm.set_value("email", "");
		const { message } = await frappe.call({
			method: "opero.mailing.membership.contact_primary_email",
			args: { contact },
		});
		if (frm.doc.custom_contact === contact) await frm.set_value("email", message);
	},
	refresh(frm) {
		frm.set_df_property("email", "read_only", !!frm.doc.custom_contact);
		if (frm.is_new()) {
			frm.set_value("custom_confirmation_status", "Pending");
		} else if (opero.mailing.is_manager() && (frm.doc.unsubscribed || frm.doc.custom_confirmation_status === "Pending")) {
			frm.add_custom_button(__("Review confirmation request"), () => {
				if (frm.is_dirty()) return frappe.msgprint(__("Save this member first."));
				// Review the current member only, including standalone email subscribers.
				opero.mailing.review({ member: frm.doc.name }, () => frm.reload_doc());
			});
		}
	},
});
