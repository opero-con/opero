function set_personnel_naming_series(frm) {
	if (!frm.is_new()) return;
	const series = {
		Staff: "OSL_EMP_.###",
		Consultant: "OSL_CON_.###",
	}[frm.doc.custom_personnel_type];
	if (series && frm.doc.naming_series !== series) {
		return frm.set_value("naming_series", series);
	}
}

frappe.ui.form.on("Employee", {
	refresh: set_personnel_naming_series,
	custom_personnel_type: set_personnel_naming_series,
});
