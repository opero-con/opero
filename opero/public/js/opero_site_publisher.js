frappe.ui.form.on("Publisher", {
	refresh(frm) {
		frm.disable_save();
		renderHistory(frm);
		if (!frappe.user.has_role("System Manager")) {
			return;
		}
		loadPending(frm);
		frm.page.set_primary_action(__("Publish to website"), () => publishWebsite(frm));
	},
});

function renderHistory(frm) {
	const rows = frm.doc.publish_log || [];
	const wrap = frm.get_field("history_html").$wrapper;
	if (!rows.length) {
		wrap.html(`<p class="text-muted">${__("No publishes yet.")}</p>`);
		return;
	}
	const items = rows
		.map((row) => {
			const when = frappe.datetime.str_to_user(row.published_on);
			const url = frappe.utils.escape_html(row.commit_url || "");
			const count = Number(row.file_count || 0);
			const files = count === 1 ? __("1 file") : __("{0} files", [count]);
			return `<li>${frappe.utils.escape_html(when)} · ${files} · <a href="${url}" target="_blank" rel="noopener">${url}</a></li>`;
		})
		.join("");
	wrap.html(`<ol>${items}</ol>`);
}

function loadPending(frm) {
	const wrap = frm.get_field("pending_html").$wrapper;
	wrap.html(`<p class="text-muted">${__("Checking the public site repository...")}</p>`);
	frappe.call({
		method: "opero.opero_site.publish.preview_publish",
		callback(r) {
			const payload = r.message || {};
			const files = payload.files || [];
			if (!files.length) {
				wrap.html(`<p class="text-muted">${frappe.utils.escape_html(payload.message || __("Nothing due."))}</p>`);
				return;
			}
			const items = files
				.map((row) => {
					const action = row.action === "delete" ? __("Remove") : __("Update");
					return `<li><strong>${frappe.utils.escape_html(action)}</strong> ${frappe.utils.escape_html(row.path)}</li>`;
				})
				.join("");
			wrap.html(`<ul>${items}</ul>`);
		},
		error() {
			wrap.html(`<p class="text-danger">${__("Could not compare Desk with GitHub.")}</p>`);
		},
	});
}

function publishWebsite(frm) {
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
							`<a href="${frappe.utils.escape_html(payload.commit_url)}" target="_blank" rel="noopener">${frappe.utils.escape_html(payload.commit_url)}</a>`,
						]
					),
				});
				frm.reload_doc();
				return;
			}
			frappe.msgprint(payload.message || __("No content changes."));
			loadPending(frm);
		},
	});
}
