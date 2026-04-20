frappe.ui.form.on("Zoho Books Settings", {
	connect_button(frm) {
		frm.save().then(() => {
			frappe.call({
				method: "opero.zoho_books.get_authorization_url",
				callback(r) {
					if (r.message) {
						window.open(r.message, "_blank");
					}
				},
			});
		});
	},

	fetch_users_button(frm) {
		frappe.call({
			method: "opero.zoho_books.get_zoho_users",
			freeze: true,
			freeze_message: "Fetching users from Zoho Books...",
			callback(r) {
				if (!r.message || !r.message.length) {
					frappe.msgprint("No users found in Zoho Books.");
					return;
				}

				const existing = {};
				(frm.doc.personnel_mapping || []).forEach(row => {
					existing[row.zoho_user_id] = row.personnel_id;
				});

				frm.clear_table("personnel_mapping");
				r.message.forEach(u => {
					frm.add_child("personnel_mapping", {
						zoho_user_id: u.user_id,
						zoho_user_name: u.name,
						personnel_id: existing[u.user_id] || "",
					});
				});
				frm.refresh_field("personnel_mapping");
				frappe.show_alert({ message: `${r.message.length} users loaded. Fill in the Employee column and save.`, indicator: "blue" });
			},
		});
	},

	fetch_projects_button(frm) {
		frappe.call({
			method: "opero.zoho_books.get_zoho_projects",
			freeze: true,
			freeze_message: "Fetching projects from Zoho Books...",
			callback(r) {
				if (!r.message || !r.message.length) {
					frappe.msgprint("No projects found in Zoho Books.");
					return;
				}

				const existing = {};
				(frm.doc.project_mapping || []).forEach(row => {
					existing[row.zoho_project_id] = row.erpnext_project;
				});

				frm.clear_table("project_mapping");
				r.message.forEach(p => {
					frm.add_child("project_mapping", {
						zoho_project_id: p.project_id,
						zoho_project_name: p.project_name,
						erpnext_project: existing[p.project_id] || "",
					});
				});
				frm.refresh_field("project_mapping");
				frappe.show_alert({ message: `${r.message.length} projects loaded. Fill in the ERPNext Project column and save.`, indicator: "blue" });
			},
		});
	},
});
