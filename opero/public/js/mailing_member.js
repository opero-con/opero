frappe.ui.form.on("Email Group Member", {
	async custom_contact(frm) {
		const contact = frm.doc.custom_contact;
		frm.set_df_property("email", "read_only", !!contact);
		if (!contact) {
			await frm.set_value("custom_mobile_no", "");
			return;
		}
		await frm.set_value("email", "");
		const { message } = await frappe.call({
			method: "opero.mailing.membership.contact_primary_email",
			args: { contact },
		});
		if (frm.doc.custom_contact === contact) await frm.set_value("email", message);
	},
	refresh(frm) {
		frm.set_df_property("email", "read_only", !!frm.doc.custom_contact);
	},
});
