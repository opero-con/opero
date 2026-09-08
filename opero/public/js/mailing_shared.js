frappe.provide("opero.mailing");

// Native Quick Entry does not run form field handlers.
frappe.ui.form.EmailGroupMemberQuickEntryForm = class extends frappe.ui.form.QuickEntryForm {
	update_doc() {
		super.update_doc();
		const field = this.dialog.fields_dict.custom_contact;
		if (field) this.dialog.doc.custom_contact = field.value || "";
	}
	render_dialog() {
		super.render_dialog();
		const dialog = this.dialog;
		const field = dialog.fields_dict.custom_contact;
		if (!field) return;
		const fill_email = async () => {
			// Link titles load asynchronously; the input may still show the previous
			// title here. Use the stored link ID rather than the displayed input.
			const contact = field.value;
			dialog.set_df_property("email", "read_only", !!contact);
			if (!contact) return;
			await dialog.set_value("email", "");
			const { message } = await frappe.call({
				method: "opero.mailing.membership.contact_primary_email",
				args: { contact },
			});
			if (field.value === contact) {
				await dialog.set_value("email", message);
				// Quick Entry hides empty read-only controls. Setting the value alone
				// does not recalculate visibility or update the displayed value.
				dialog.get_field("email").refresh();
			}
		};
		dialog.set_df_property("email", "read_only", !!field.value);
		field.df.change = fill_email;
	}
};

Object.assign(opero.mailing, {
	is_manager() {
		return frappe.session.user === "Administrator" || frappe.user_roles.includes("Newsletter Manager");
	},
	async list_options(txt) {
		const { message } = await frappe.call({
			method: "opero.mailing.membership.search_lists",
			args: { doctype: "Email Group", txt: txt || "", searchfield: "name", start: 0, page_len: 50, filters: {} },
		});
		return (message || []).map(([value]) => ({ value, label: value }));
	},
	group_field() {
		return { fieldname: "mailing_lists", label: __("Mailing Lists"), fieldtype: "MultiSelectList",
			get_data: (txt) => opero.mailing.list_options(txt) };
	},
	status_html(rows) {
		const escape = frappe.utils.escape_html;
		if (!rows.length) return `<p class="text-muted">${__("No mailing-list memberships.")}</p>`;
		return `<table class="table table-bordered"><thead><tr><th>${__("Mailing List")}</th><th>${__("Status")}</th></tr></thead><tbody>${rows.map((r) =>
			`<tr><td>${escape(r.mailing_list)}</td><td>${escape(__(r.status || r.subscription_status || "No email"))}</td></tr>`).join("")}</tbody></table>`;
	},
	bulk(contacts, done, mailing_list) {
		if (!contacts.length) return frappe.msgprint(__("Select Contacts first."));
		const group = this.group_field();
		group.reqd = 1;
		if (mailing_list) group.default = [mailing_list];
		const d = new frappe.ui.Dialog({
			title: __("Manage Mailing Lists"),
			fields: [group, { fieldname: "action", label: __("Action"), fieldtype: "Select", options: "add\nremove", default: "add" },
				{ fieldtype: "HTML", options: `<p class="text-muted">${__("Contacts sharing a primary email share memberships. Changes apply to that address. No email will be sent.")}</p>` }],
			primary_action_label: __("Save memberships"),
			async primary_action(values) {
				await frappe.call({ method: "opero.mailing.membership.bulk_membership", args: { contacts, ...values }, freeze: true });
				d.hide();
				frappe.show_alert({ message: __("Memberships saved. No emails were sent."), indicator: "green" });
				if (done) done();
			},
		});
		d.show();
	},
});
