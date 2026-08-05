// Opero: client scripts for Item
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// --- Item naming series ---
frappe.ui.form.on("Item", {
	setup(frm) {
		frm.toggle_reqd("item_code", false);
	},
	onload(frm) {
		frm.toggle_reqd("item_code", false);
	},
	refresh(frm) {
		frm.toggle_reqd("item_code", false);
	},
});
