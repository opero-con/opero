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

const GROUP_ORDER = ["Site pages", "Publications", "Team", "Enterprises", "Other"];

function renderPending(wrap, payload) {
	const files = (payload && payload.files) || [];
	if (!files.length) {
		wrap.html(`<p class="text-muted">${frappe.utils.escape_html(payload.message || __("Nothing due."))}</p>`);
		return;
	}
	const groups = {};
	for (const row of files) {
		const group = row.group || __("Other");
		(groups[group] = groups[group] || []).push(row);
	}
	const names = Object.keys(groups).sort((a, b) => GROUP_ORDER.indexOf(a) - GROUP_ORDER.indexOf(b));
	const sections = names
		.map((name) => {
			const items = groups[name]
				.slice()
				.sort((a, b) => (a.title || a.path).localeCompare(b.title || b.path))
				.map((row) => `<li>${pendingRowHtml(row)}</li>`)
				.join("");
			return `<div class="opero-pending-group">
				<p class="opero-pending-group__title">${frappe.utils.escape_html(__(name))}</p>
				<ul>${items}</ul>
			</div>`;
		})
		.join("");
	wrap.html(sections);
	bindPendingRowClicks(wrap);
}

function pendingRowHtml(row) {
	const action = row.action === "delete" ? __("Remove") : __("Update");
	const title = frappe.utils.escape_html(row.title || row.path);
	const path = frappe.utils.escape_html(row.path);
	const diffLink = `<a href="#" class="opero-pending-diff" data-path="${path}">${title}</a>`;
	let openLink = "";
	if (row.is_single && row.doctype) {
		const doctype = frappe.utils.escape_html(row.doctype);
		openLink = ` <a href="#" class="text-muted opero-pending-open" data-doctype="${doctype}" title="${__("Open record")}">↗</a>`;
	} else if (row.doctype && row.docname) {
		const doctype = frappe.utils.escape_html(row.doctype);
		const docname = frappe.utils.escape_html(row.docname);
		openLink = ` <a href="#" class="text-muted opero-pending-open" data-doctype="${doctype}" data-docname="${docname}" title="${__("Open record")}">↗</a>`;
	}
	return `<strong>${frappe.utils.escape_html(action)}</strong> ${diffLink}${openLink}`;
}

function bindPendingRowClicks(wrap) {
	wrap.find(".opero-pending-diff").on("click", (e) => {
		e.preventDefault();
		showContentDiff($(e.currentTarget).data("path"));
	});
	wrap.find(".opero-pending-open").on("click", (e) => {
		e.preventDefault();
		const el = $(e.currentTarget);
		const doctype = el.data("doctype");
		const docname = el.data("docname");
		if (docname) {
			frappe.set_route("Form", doctype, docname);
		} else {
			frappe.set_route("Form", doctype);
		}
	});
}

function diffLineClass(line) {
	if (line.startsWith("+")) {
		return "is-add";
	}
	if (line.startsWith("-")) {
		return "is-del";
	}
	if (line.startsWith("@@")) {
		return "is-hunk";
	}
	return "";
}

function renderDiffHtml(payload) {
	if (payload.is_binary) {
		return `<p class="text-muted">${__("Binary file changed; no text diff available.")}</p>`;
	}
	if (payload.is_new) {
		const lines = (payload.diff || [])
			.map((line) => `<div class="opero-diff__line is-add">+ ${frappe.utils.escape_html(line)}</div>`)
			.join("");
		return `<div class="opero-diff">${lines}</div>`;
	}
	if (payload.is_delete) {
		const lines = (payload.diff || [])
			.map((line) => `<div class="opero-diff__line is-del">- ${frappe.utils.escape_html(line)}</div>`)
			.join("");
		return `<div class="opero-diff">${lines}</div>`;
	}
	const lines = (payload.diff || []).filter((line) => !line.startsWith("---") && !line.startsWith("+++"));
	if (!lines.length) {
		return `<p class="text-muted">${frappe.utils.escape_html(payload.message || __("No differences."))}</p>`;
	}
	const rendered = lines
		.map((line) => `<div class="opero-diff__line ${diffLineClass(line)}">${frappe.utils.escape_html(line)}</div>`)
		.join("");
	return `<div class="opero-diff">${rendered}</div>`;
}

function showContentDiff(path) {
	const dialog = new frappe.ui.Dialog({
		title: __("Pending change"),
		fields: [{ fieldtype: "HTML", fieldname: "diff" }],
	});
	dialog.fields_dict.diff.$wrapper.html(`<p class="text-muted">${__("Loading...")}</p>`);
	dialog.show();
	frappe.call({
		method: "opero.opero_site.publish.preview_content_diff",
		args: { path },
		callback(r) {
			const payload = r.message || {};
			dialog.set_title(payload.title || path);
			dialog.fields_dict.diff.$wrapper.html(renderDiffHtml(payload));
		},
		error() {
			dialog.fields_dict.diff.$wrapper.html(`<p class="text-danger">${__("Could not load the diff.")}</p>`);
		},
	});
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
		byPath[row.path] = row;
	}
	for (const row of incoming) {
		if (row && row.path) {
			byPath[row.path] = row;
		}
	}
	const files = Object.keys(byPath)
		.sort()
		.map((path) => byPath[path]);
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
