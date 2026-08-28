frappe.ui.form.on("Publication", {
	setup(frm) {
		const field = frm.get_field("body");
		if (!field) {
			return;
		}
		field.df.get_toolbar_options = () => [
			[{ header: [2, 3, false] }],
			["link"],
			[{ list: "bullet" }, { list: "ordered" }],
		];
	},
});
