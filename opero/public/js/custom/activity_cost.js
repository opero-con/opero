// Opero: client scripts for Activity Cost
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// --- Day Rate Conversion ---
frappe.ui.form.on("Activity Cost", {
	custom_day_billing_rate(frm) {
		calculate_billing_rate(frm);
	},
	custom_day_costing_rate(frm) {
		calculate_costing_rate(frm);
	},
	billing_rate(frm) {
		calculate_billing_rate(frm);
	},
	costing_rate(frm) {
		calculate_costing_rate(frm);
	},
	custom_currency(frm) {
		calculate_billing_rate(frm);
		calculate_costing_rate(frm);
	},
	custom_exchange_rate(frm) {
		calculate_billing_rate(frm);
		calculate_costing_rate(frm);
	},
});

function calculate_billing_rate(frm) {
	if (!frm.doc.custom_day_billing_rate) {
		frappe.msgprint(__("Please set Custom Day Billing Rate."));
		return;
	}

	frappe.db.get_single_value("HR Settings", "standard_working_hours").then((hours) => {
		if (!hours) {
			frappe.msgprint(__("Standard Working Hours is not set in HR Settings."));
			return;
		}
		let rate = frm.doc.custom_day_billing_rate / hours;
		if (frm.doc.custom_currency && frm.doc.custom_exchange_rate) {
			rate =
				(frm.doc.custom_day_billing_rate * frm.doc.custom_exchange_rate) / hours;
		}
		frm.set_value("billing_rate", rate);
	});
}

function calculate_costing_rate(frm) {
	if (!frm.doc.custom_day_costing_rate) {
		frappe.msgprint(__("Please set Custom Day Costing Rate."));
		return;
	}

	frappe.db.get_single_value("HR Settings", "standard_working_hours").then((hours) => {
		if (!hours) {
			frappe.msgprint(__("Standard Working Hours is not set in HR Settings."));
			return;
		}
		let rate = frm.doc.custom_day_costing_rate / hours;
		if (frm.doc.custom_currency && frm.doc.custom_exchange_rate) {
			rate =
				(frm.doc.custom_day_costing_rate * frm.doc.custom_exchange_rate) / hours;
		}
		frm.set_value("costing_rate", rate);
	});
}
