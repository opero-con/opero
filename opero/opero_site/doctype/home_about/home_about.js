frappe.ui.form.on("Home About", {
	setup(frm) {
		const field = frm.get_field("about_body");
		if (!field) {
			return;
		}
		// About frontmatter is a flat paragraph list — no headings, lists, or link buttons.
		field.df.get_toolbar_options = () => [];
	},
});
