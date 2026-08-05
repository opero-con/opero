// Opero: client scripts for Leave Application
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// --- Auto Submit LA if Approved ---
frappe.ui.form.on("Leave Application", {
	onload(frm) {
		frm._auto_submitted = false;
	},

	after_save(frm) {
		if (
			frm.doc.status === "Approved" &&
			frm.doc.docstatus === 0 &&
			!frm._auto_submitted
		) {
			frm._auto_submitted = true;
			frappe.call({
				method: "frappe.client.submit",
				args: {
					doc: frm.doc,
				},
				callback(r) {
					if (!r.exc) {
						frappe.show_alert({
							message: __("Leave Application auto-submitted."),
							indicator: "green",
						});
						frm.reload_doc();
					} else {
						frappe.msgprint(__("Submission failed. Please submit manually."));
					}
				},
			});
		}
	},
});

// --- Name Autohide ---
frappe.ui.form.on("Leave Application", {
	employee(frm) {
		check_employee_numeric(frm);
	},
	refresh(frm) {
		check_employee_numeric(frm);
	},
});

function check_employee_numeric(frm) {
	if (!frm.doc.employee) {
		frm.set_df_property("employee_name", "hidden", 1);
		return;
	}

	frappe.db.get_value("Employee", frm.doc.employee, "employee_name").then((r) => {
		const employeeName = (r.message && r.message.employee_name) || "";
		// Show employee_name when it contains digits (numeric-looking names).
		frm.set_df_property("employee_name", "hidden", /\d/.test(employeeName) ? 0 : 1);
	});
}
