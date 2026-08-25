frappe.ui.form.on("Opero Site Settings", {
	refresh(frm) {
		if (!frappe.user.has_role("System Manager")) {
			return;
		}
		frm.add_custom_button(__("Publish to website"), () => {
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
							message: __("Opened {0}", [`<a href="${frappe.utils.escape_html(payload.pr_url)}" target="_blank">${frappe.utils.escape_html(payload.pr_url)}</a>`]),
						});
						return;
					}
					frappe.msgprint(payload.message || __("No content changes."));
				},
			});
		});
	},
});
