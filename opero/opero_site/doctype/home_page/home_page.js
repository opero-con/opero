frappe.ui.form.on("Home Page", {
	setup(frm) {
		const field = frm.get_field("about_body");
		if (!field) {
			return;
		}
		// About frontmatter is a flat paragraph list — no headings, lists, or link buttons.
		field.df.get_toolbar_options = () => [];
	},
	refresh(frm) {
		const field = frm.get_field("hero_description");
		if (field && field.$input && !field.$input.data("opero-autosize")) {
			field.$input.data("opero-autosize", 1);
			field.$input.on("input", () => fit_hero_description(frm));
		}
		fit_hero_description(frm);
	},
	hero_description(frm) {
		fit_hero_description(frm);
	},
});

function fit_hero_description(frm) {
	const field = frm.get_field("hero_description");
	const input = field && field.$input && field.$input.get(0);
	if (!input) {
		return;
	}
	input.rows = 1;
	input.style.overflowY = "hidden";
	input.style.resize = "none";
	input.style.height = "auto";
	input.style.height = `${input.scrollHeight}px`;
}
