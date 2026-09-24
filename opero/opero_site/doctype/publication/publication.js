frappe.ui.form.on("Publication", {
	refresh(frm) {
		const field = frm.get_field("summary");
		if (field && field.$input && !field.$input.data("opero-autosize")) {
			field.$input.data("opero-autosize", 1);
			field.$input.on("input", () => fit_summary(frm));
		}
		fit_summary(frm);
	},
	summary(frm) {
		fit_summary(frm);
	},
});

// Fit the text plus one spare line, so an empty summary shows two lines.
function fit_summary(frm) {
	const field = frm.get_field("summary");
	const input = field && field.$input && field.$input.get(0);
	if (!input) {
		return;
	}
	input.rows = 1;
	input.style.overflowY = "hidden";
	input.style.resize = "none";
	input.style.height = "auto";
	const line_height = parseFloat(getComputedStyle(input).lineHeight);
	input.style.height = `${input.scrollHeight + line_height}px`;
}
