frappe.ui.form.on("Site Settings", {
	refresh(frm) {
		if (!frappe.user.has_role("System Manager")) {
			return;
		}
		frm.add_custom_button(
			__("Load from website content"),
			() => {
				frappe.confirm(
					__(
						"Replace Opero Site records with Markdown from the public content repository? Extra team members on this site are kept."
					),
					() => {
						frappe.call({
							method: "opero.opero_site.load.load_from_website",
							freeze: true,
							freeze_message: __("Loading content from GitHub..."),
							callback(r) {
								const payload = r.message || {};
								frm.reload_doc();
								frappe.msgprint(payload.message || __("Content loaded."));
							},
						});
					}
				);
			},
			__("Website")
		);
	},
});
