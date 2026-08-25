frappe.ui.form.on("Opero Site Settings", {
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
		frm.add_custom_button(
			__("Publish to website"),
			() => {
				frappe.call({
					method: "opero.opero_site.publish.publish_to_website",
					freeze: true,
					freeze_message: __("Publishing to the public site..."),
					callback(r) {
						const payload = r.message || {};
						if (payload.commit_url) {
							frappe.msgprint({
								title: __("Published to website"),
								indicator: "green",
								message: __(
									"Committed {0}",
									[
										`<a href="${frappe.utils.escape_html(payload.commit_url)}" target="_blank">${frappe.utils.escape_html(payload.commit_url)}</a>`,
									]
								),
							});
							return;
						}
						frappe.msgprint(payload.message || __("No content changes."));
					},
				});
			},
			__("Website")
		);
	},
});
