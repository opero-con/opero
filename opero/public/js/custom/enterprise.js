frappe.ui.form.on("Enterprise", {
	setup(frm) {
		frm.set_query("business_category", () => ({
			filters: {
				is_group: 0,
			},
		}));

		frm.set_query("enterprise_primary_contact", (doc) => ({
			query: "opero.opero.doctype.enterprise.enterprise.get_enterprise_primary",
			filters: {
				enterprise: doc.name,
				type: "Contact",
			},
		}));

		frm.set_query("enterprise_primary_address", (doc) => ({
			query: "opero.opero.doctype.enterprise.enterprise.get_enterprise_primary",
			filters: {
				enterprise: doc.name,
				type: "Address",
			},
		}));
	},

	refresh(frm) {
		if (frm.doc.__islocal) {
			hide_field(["address_html", "contact_html"]);
			frappe.contacts.clear_address_and_contact(frm);
		} else {
			unhide_field(["address_html", "contact_html"]);
			frappe.contacts.render_address_and_contact(frm);
		}
	},

	enterprise_primary_address(frm) {
		if (!frm.doc.enterprise_primary_address) {
			frm.set_value("primary_address", "");
			return;
		}

		frappe.call({
			method: "frappe.contacts.doctype.address.address.get_address_display",
			args: {
				address_dict: frm.doc.enterprise_primary_address,
			},
			callback(r) {
				frm.set_value("primary_address", r.message);
			},
		});
	},

	enterprise_primary_contact(frm) {
		if (!frm.doc.enterprise_primary_contact) {
			frm.set_value("mobile_no", "");
			frm.set_value("email_id", "");
			return;
		}

		frappe.call({
			method: "frappe.contacts.doctype.contact.contact.get_contact_details",
			args: {
				contact: frm.doc.enterprise_primary_contact,
			},
			callback(r) {
				if (!r.message) return;
				frm.set_value("mobile_no", r.message.contact_mobile || r.message.contact_phone || "");
				frm.set_value("email_id", r.message.contact_email || "");
			},
		});
	},
});
