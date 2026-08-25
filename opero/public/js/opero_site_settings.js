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
					freeze_message: __("Opening a content pull request..."),
					callback(r) {
						const payload = r.message || {};
						if (payload.pr_url) {
							frappe.msgprint({
								title: __("Content pull request"),
								indicator: "green",
								message: __(
									"Opened {0}",
									[
										`<a href="${frappe.utils.escape_html(payload.pr_url)}" target="_blank">${frappe.utils.escape_html(payload.pr_url)}</a>`,
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
