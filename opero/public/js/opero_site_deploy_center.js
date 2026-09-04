frappe.ui.form.on("Deploy Center", {
	refresh(frm) {
		frm.disable_save();
		renderHistory(frm);
		bindPendingPush(frm);
		if (!frm.has_perm("write")) {
			return;
		}
		loadPending(frm);
		frm.page.set_primary_action(__("Deploy to website"), () => deployWebsite(frm));
		frm.page.set_secondary_action(__("Refresh"), () => syncPending(frm), "refresh");
	},
});

const PROGRESS_EVENT = "opero_site_progress";
const PENDING_EVENT = "opero_site_pending";

function renderHistory(frm) {
	const rows = frm.doc.deploy_log || [];
	const wrap = frm.get_field("history_html").$wrapper;
	if (!rows.length) {
		wrap.html(`<p class="text-muted">${__("No deploys yet.")}</p>`);
		return;
	}
	const items = rows
		.map((row) => {
			const when = frappe.datetime.str_to_user(row.deployed_on);
			const who = deployedByLabel(row.deployed_by);
			const count = Number(row.file_count || 0);
			const files = count === 1 ? __("1 file") : __("{0} files", [count]);
			const parts = [frappe.utils.escape_html(when)];
			if (who) {
				parts.push(frappe.utils.escape_html(who));
			}
			parts.push(frappe.utils.escape_html(files));
			parts.push(commitLink(row.commit_url, row.sha));
			return `<li>${parts.join(" · ")}</li>`;
		})
		.join("");
	wrap.html(`<ol>${items}</ol>`);
}

function deployedByLabel(user) {
	if (!user) {
		return "";
	}
	return (frappe.user_info(user) || {}).fullname || user;
}

function shortSha(sha, url) {
	const fromSha = String(sha || "").trim();
	if (fromSha) {
		return fromSha.slice(0, 7);
	}
	const path = String(url || "").split("/").pop() || "";
	return path.slice(0, 7);
}

function commitLink(url, sha) {
	const href = frappe.utils.escape_html(url || "");
	const abbrev = shortSha(sha, url);
	const label = frappe.utils.escape_html(
		abbrev ? __("commit {0}", [abbrev]) : __("commit")
	);
	if (!href || !abbrev) {
		return label;
	}
	return `<a href="${href}" target="_blank" rel="noopener">${label}</a>`;
}

function setBusy(frm, busy) {
	frm._opero_busy = busy;
	if (frm.page.btn_primary) {
		frm.page.btn_primary.prop("disabled", busy);
	}
	if (frm.page.btn_secondary) {
		frm.page.btn_secondary.prop("disabled", busy);
	}
}

function showProgress(wrap, label) {
	wrap.html(`<div class="opero-deploy-progress">
		<div class="progress" style="height: 8px;">
			<div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 100%;"></div>
		</div>
		<p class="text-muted opero-deploy-label" style="margin-top: 8px;">${frappe.utils.escape_html(label)}</p>
	</div>`);
}

function bindProgress(wrap) {
	if (!frappe.realtime || !frappe.realtime.on) {
		return () => {};
	}
	if (frappe.realtime.off) {
		frappe.realtime.off(PROGRESS_EVENT);
	}
	const handler = (data) => {
		const total = Number(data.total || 0);
		const done = Number(data.done || 0);
		const pct = total ? Math.max(4, Math.round((done / total) * 100)) : 100;
		const bar = wrap.find(".progress-bar");
		bar.removeClass("progress-bar-striped progress-bar-animated");
		bar.css("width", `${pct}%`);
		if (data.path) {
			wrap.find(".opero-deploy-label").text(data.path);
		}
	};
	frappe.realtime.on(PROGRESS_EVENT, handler);
	return () => {
		if (frappe.realtime.off) {
			frappe.realtime.off(PROGRESS_EVENT);
		}
	};
}

function renderPending(wrap, payload) {
	const files = (payload && payload.files) || [];
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
}

function bindPendingPush(frm) {
	if (!frappe.realtime || !frappe.realtime.on || frm._opero_pending_bound) {
		return;
	}
	frm._opero_pending_bound = true;
	frappe.realtime.on(PENDING_EVENT, (data) => {
		pushPending(frm, data);
	});
}

function pushPending(frm, data) {
	const incoming = (data && data.files) || [];
	if (!incoming.length) {
		return;
	}
	if (frm._opero_busy) {
		frm._opero_pending_queue = (frm._opero_pending_queue || []).concat(incoming);
		return;
	}
	applyPendingFiles(frm, incoming);
}

function applyPendingQueue(frm) {
	const queued = frm._opero_pending_queue || [];
	frm._opero_pending_queue = [];
	if (queued.length) {
		applyPendingFiles(frm, queued);
	}
}

function applyPendingFiles(frm, incoming) {
	const byPath = {};
	for (const row of frm._opero_pending_files || []) {
		byPath[row.path] = row.action;
	}
	for (const row of incoming) {
		if (row && row.path) {
			byPath[row.path] = row.action;
		}
	}
	const files = Object.keys(byPath)
		.sort()
		.map((path) => ({ path, action: byPath[path] }));
	frm._opero_pending_files = files;
	renderPending(frm.get_field("pending_html").$wrapper, { files });
}

function loadPending(frm) {
	if (frm._opero_busy) {
		return;
	}
	const wrap = frm.get_field("pending_html").$wrapper;
	setBusy(frm, true);
	frappe.call({
		method: "opero.opero_site.publish.preview_pending",
		callback(r) {
			setBusy(frm, false);
			const payload = r.message || {};
			frm._opero_pending_files = payload.files || [];
			renderPending(wrap, payload);
			applyPendingQueue(frm);
		},
		error() {
			setBusy(frm, false);
			wrap.html(`<p class="text-danger">${__("Could not load pending website changes.")}</p>`);
			applyPendingQueue(frm);
		},
	});
}

function syncPending(frm) {
	if (frm._opero_busy) {
		return;
	}
	const wrap = frm.get_field("pending_html").$wrapper;
	showProgress(wrap, __("Checking the public site repository..."));
	const stop = bindProgress(wrap);
	setBusy(frm, true);
	frappe.call({
		method: "opero.opero_site.publish.preview_deploy",
		callback(r) {
			stop();
			setBusy(frm, false);
			const payload = r.message || {};
			frm._opero_pending_files = payload.files || [];
			renderPending(wrap, payload);
			applyPendingQueue(frm);
		},
		error() {
			stop();
			setBusy(frm, false);
			wrap.html(`<p class="text-danger">${__("Could not compare Desk with GitHub.")}</p>`);
			applyPendingQueue(frm);
		},
	});
}

function deployWebsite(frm) {
	if (frm._opero_busy) {
		return;
	}
	const wrap = frm.get_field("pending_html").$wrapper;
	showProgress(wrap, __("Deploying to the public site..."));
	const stop = bindProgress(wrap);
	setBusy(frm, true);
	frappe.call({
		method: "opero.opero_site.publish.deploy_to_website",
		callback(r) {
			stop();
			setBusy(frm, false);
			const payload = r.message || {};
			if (payload.commit_url) {
				frappe.msgprint({
					title: __("Deployed to website"),
					indicator: "green",
					message: commitLink(payload.commit_url, payload.sha),
				});
				frm.reload_doc();
				return;
			}
			frappe.msgprint(payload.message || __("No content changes."));
			loadPending(frm);
		},
		error() {
			stop();
			setBusy(frm, false);
			wrap.html(`<p class="text-danger">${__("Could not deploy to GitHub.")}</p>`);
		},
	});
}
