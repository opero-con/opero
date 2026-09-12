frappe.ui.form.on("Site Settings", {
	refresh(frm) {
		if (!frm.has_perm("write")) {
			return;
		}
		frm.add_custom_button(
			__("Import website content"),
			() => {
				frappe.confirm(
					__(
						"Import changed website content from the public repository? This overwrites corresponding local website fields. Extra personnel on this site are kept."
					),
					() => {
						frappe.call({
							method: "opero.opero_site.load.load_from_website",
							freeze: true,
							freeze_message: __("Importing website content..."),
							callback(r) {
								const payload = r.message || {};
								frm.reload_doc();
								frappe.msgprint(payload.message || __("Website content imported."));
							},
						});
					}
				);
			},
			__("Website")
		);
	},
});
