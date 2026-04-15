frappe.provide("opero");

frappe.pages["flow-hub"].on_page_load = function (wrapper) {
	wrapper.flow_hub = new opero.FlowHubPage(wrapper);
};

frappe.pages["flow-hub"].on_page_show = function (wrapper) {
	if (wrapper.flow_hub) {
		wrapper.flow_hub.refresh();
	}
};

opero.FlowHubPage = class FlowHubPage {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.loading = false;
		this.snapshot = {};

		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Flow Hub"),
			single_column: true,
		});

		this.page.set_primary_action(__("Refresh"), () => this.refresh({ force: true }), "refresh");
		this.page.add_menu_item(__("Open Action Queue"), () => this.open_action_queue());
		frappe.breadcrumbs.add("Opero");

		this._inject_styles();
		$(this.page.main).empty();
		this.$root = $("<div class='fh'></div>").appendTo(this.page.main);
		this.render_loading();
		this.refresh();
	}

	_inject_styles() {
		if (document.getElementById("fh-styles")) return;
		const style = document.createElement("style");
		style.id = "fh-styles";
		style.textContent = `
			.fh {
				padding: 1rem;
				min-height: calc(100vh - 120px);
				background: #f8fafc;
				font-family: -apple-system, "Inter", "Segoe UI", sans-serif;
			}

			/* ── Status bar ─────────────────────────────────────── */
			.fh-status {
				display: flex;
				align-items: center;
				flex-wrap: wrap;
				gap: 0.45rem 0.6rem;
				padding: 0.55rem 0.8rem;
				border-radius: 10px;
				background: #ffffff;
				border: 1px solid #e2e8f0;
				margin-bottom: 0.65rem;
			}
			.fh-status__msg {
				flex: 0 0 100%;
				font-size: 0.88rem;
				font-weight: 600;
				color: #0f172a;
			}
			.fh-status__msg.is-urgent { color: #b91c1c; }
			.fh-status__msg.is-clear  { color: #047857; }
			.fh-status__time {
				flex: 1 1 auto;
				font-size: 0.72rem;
				color: #94a3b8;
			}
			.fh-status__btn {
				border: 1px solid #e2e8f0;
				background: #f8fafc;
				color: #1e40af;
				padding: 0.28rem 0.6rem;
				border-radius: 7px;
				font-size: 0.76rem;
				font-weight: 600;
				cursor: pointer;
				transition: background 130ms;
				white-space: nowrap;
				flex-shrink: 0;
			}
			.fh-status__btn:hover { background: #eff6ff; }

			/* ── Count cards ────────────────────────────────────── */
			.fh-counts {
				display: grid;
				grid-template-columns: repeat(4, 1fr);
				gap: 0.65rem;
				margin-bottom: 0.65rem;
			}
			.fh-card {
				background: #ffffff;
				border: 1px solid #e2e8f0;
				border-top: 3px solid var(--fh-accent, #2563eb);
				border-radius: 10px;
				padding: 0.7rem 0.8rem;
				text-align: left;
				cursor: pointer;
				transition: transform 140ms, box-shadow 140ms;
			}
			.fh-card:hover {
				transform: translateY(-2px);
				box-shadow: 0 4px 14px rgba(0,0,0,0.07);
			}
			.fh-card__label {
				font-size: 0.69rem;
				color: #64748b;
				text-transform: uppercase;
				letter-spacing: 0.06em;
				margin-bottom: 0.3rem;
			}
			.fh-card__value {
				font-size: 1.55rem;
				font-weight: 700;
				color: #0f172a;
				line-height: 1;
			}
			.fh-card__value.is-zero { color: #cbd5e1; }

			/* ── Two-column body ────────────────────────────────── */
			.fh-body {
				display: grid;
				grid-template-columns: 1.3fr 1fr;
				gap: 0.65rem;
			}
			.fh-right { display: flex; flex-direction: column; gap: 0.65rem; }

			/* ── Shared panel chrome ────────────────────────────── */
			.fh-panel {
				background: #ffffff;
				border: 1px solid #e2e8f0;
				border-radius: 10px;
				overflow: hidden;
			}
			.fh-panel__head {
				padding: 0.65rem 0.75rem 0;
			}
			.fh-panel__title {
				font-size: 0.69rem;
				font-weight: 700;
				color: #64748b;
				text-transform: uppercase;
				letter-spacing: 0.07em;
				margin: 0 0 0.1rem;
			}
			.fh-panel__sub {
				font-size: 0.71rem;
				color: #94a3b8;
				margin: 0 0 0.45rem;
			}

			/* ── Focus queue ────────────────────────────────────── */
			.fh-queue { padding: 0 0.5rem 0.6rem; }
			.fh-item {
				display: block;
				width: 100%;
				text-align: left;
				padding: 0.5rem 0.6rem;
				margin-bottom: 0.35rem;
				border-radius: 8px;
				border: 1px solid #f1f5f9;
				border-left: 4px solid var(--fh-band-color, #e2e8f0);
				background: #fcfcfd;
				cursor: pointer;
				transition: background 130ms;
			}
			.fh-item:hover { background: #f1f5f9; }
			.fh-item:last-child { margin-bottom: 0; }
			.fh-item__title {
				font-size: 0.83rem;
				font-weight: 600;
				color: #0f172a;
				line-height: 1.3;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
				margin-bottom: 0.22rem;
			}
			.fh-item__meta {
				display: flex;
				align-items: center;
				gap: 0.35rem;
				flex-wrap: wrap;
				font-size: 0.71rem;
				color: #64748b;
			}

			/* Urgency band colours */
			.fh-band-overdue   { --fh-band-color: #ef4444; }
			.fh-band-due_today { --fh-band-color: #f97316; }
			.fh-band-stale     { --fh-band-color: #7c3aed; }
			.fh-band-due_soon  { --fh-band-color: #2563eb; }
			.fh-band-active    { --fh-band-color: #e2e8f0; }

			/* Urgency tag pill */
			.fh-tag {
				padding: 0.11rem 0.34rem;
				border-radius: 4px;
				font-size: 0.65rem;
				font-weight: 700;
				text-transform: uppercase;
				letter-spacing: 0.06em;
			}
			.fh-tag.band-overdue   { background: #fef2f2; color: #b91c1c; }
			.fh-tag.band-due_today { background: #fff7ed; color: #c2410c; }
			.fh-tag.band-stale     { background: #faf5ff; color: #6d28d9; }
			.fh-tag.band-due_soon  { background: #eff6ff; color: #1d4ed8; }

			/* Priority pill */
			.fh-priority {
				padding: 0.1rem 0.32rem;
				border-radius: 4px;
				background: #fff7ed;
				color: #b45309;
				font-size: 0.65rem;
				font-weight: 700;
				text-transform: uppercase;
				letter-spacing: 0.04em;
			}

			.fh-empty {
				padding: 1.2rem 0.75rem;
				font-size: 0.8rem;
				color: #94a3b8;
				text-align: center;
			}
			.fh-empty.is-clear { color: #047857; font-weight: 600; }

			/* ── Risk signals ───────────────────────────────────── */
			.fh-risk { padding: 0 0.4rem 0.5rem; }
			.fh-risk-row {
				display: flex;
				align-items: center;
				padding: 0.42rem 0.45rem;
				border-radius: 7px;
				cursor: pointer;
				transition: background 130ms;
				gap: 0.5rem;
			}
			.fh-risk-row:hover { background: #f8fafc; }
			.fh-risk-row__label {
				flex: 1;
				font-size: 0.79rem;
				color: #475569;
			}
			.fh-risk-row__value {
				font-size: 0.92rem;
				font-weight: 700;
				color: #0f172a;
				min-width: 1.4rem;
				text-align: right;
			}
			.fh-risk-row__value.is-zero { color: #cbd5e1; }
			.fh-risk-row__arrow { font-size: 0.7rem; color: #cbd5e1; }
			.fh-divider {
				border: none;
				border-top: 1px solid #f8fafc;
				margin: 0 0.45rem;
			}

			/* ── Throughput ─────────────────────────────────────── */
			.fh-throughput { padding: 0 0.6rem 0.65rem; }
			.fh-trow {
				display: flex;
				align-items: center;
				gap: 0.5rem;
				padding: 0.28rem 0;
				font-size: 0.79rem;
			}
			.fh-trow__label {
				width: 4rem;
				color: #64748b;
				flex-shrink: 0;
			}
			.fh-trow__bar-wrap {
				flex: 1;
				height: 5px;
				background: #f1f5f9;
				border-radius: 3px;
				overflow: hidden;
			}
			.fh-trow__bar {
				height: 100%;
				border-radius: 3px;
				transition: width 380ms ease;
				min-width: 2px;
			}
			.fh-trow__bar.is-created { background: #2563eb; }
			.fh-trow__bar.is-closed  { background: #059669; }
			.fh-trow__count {
				width: 1.4rem;
				text-align: right;
				font-weight: 700;
				color: #0f172a;
				flex-shrink: 0;
			}
			.fh-net {
				margin-top: 0.45rem;
				padding: 0.32rem 0.5rem;
				border-radius: 7px;
				font-size: 0.76rem;
				font-weight: 600;
				text-align: center;
			}
			.fh-net.is-ahead   { background: #f0fdf4; color: #047857; }
			.fh-net.is-behind  { background: #fff1f2; color: #be123c; }
			.fh-net.is-neutral { background: #f8fafc; color: #64748b; }

			/* ── Skeleton / error ───────────────────────────────── */
			.fh-skeleton {
				border-radius: 10px;
				background: linear-gradient(90deg, #e2e8f0 0%, #f8fafc 50%, #e2e8f0 100%);
				background-size: 200% 100%;
				animation: fh-shimmer 1.2s linear infinite;
			}
			.fh-error {
				padding: 0.8rem;
				border: 1px solid #fecaca;
				background: #fff1f2;
				color: #9f1239;
				border-radius: 10px;
				font-size: 0.82rem;
			}
			@keyframes fh-shimmer {
				0%   { background-position: 200% 0; }
				100% { background-position: -200% 0; }
			}

			/* ── Responsive ─────────────────────────────────────── */
			@media (max-width: 960px) {
				.fh-body   { grid-template-columns: 1fr; }
				.fh-counts { grid-template-columns: repeat(2, 1fr); }
			}
			@media (max-width: 480px) {
				.fh { padding: 0.5rem; }
			}
		`;
		document.head.appendChild(style);
	}

	// ── Loading / error states ────────────────────────────────────────

	render_loading() {
		this.$root.html(`
			<div class="fh-skeleton" style="height:40px; margin-bottom:0.65rem;"></div>
			<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:0.65rem; margin-bottom:0.65rem;">
				${Array(4).fill('<div class="fh-skeleton" style="height:72px;"></div>').join("")}
			</div>
			<div style="display:grid; grid-template-columns:1.3fr 1fr; gap:0.65rem;">
				<div class="fh-skeleton" style="height:320px;"></div>
				<div style="display:flex; flex-direction:column; gap:0.65rem;">
					<div class="fh-skeleton" style="height:148px;"></div>
					<div class="fh-skeleton" style="height:148px;"></div>
				</div>
			</div>
		`);
	}

	render_error() {
		this.$root.html(
			`<div class="fh-error">${this.esc(__("Flow Hub could not load. Please refresh once."))}</div>`
		);
	}

	// ── Data fetch ───────────────────────────────────────────────────

	refresh({ force = false } = {}) {
		if (this.loading) return;
		this.loading = true;
		this.render_loading();
		frappe.call({
			method: "opero.todo_dashboard.get_flow_hub_snapshot",
			args: { force_refresh: force ? 1 : 0 },
			callback: (r) => {
				this.loading = false;
				this.snapshot = r.message || {};
				this.render();
			},
			error: () => {
				this.loading = false;
				this.render_error();
			},
		});
	}

	// ── Main render ──────────────────────────────────────────────────

	render() {
		const s = this.snapshot;
		const attention = s.attention || "";
		const isAllClear = attention.startsWith("All clear");

		this.$root.html(`
			${this._render_status_bar(attention, isAllClear, s.updated_at)}
			${this._render_counts(s.counts || [])}
			<div class="fh-body">
				${this._render_focus_queue(s.focus_queue || [])}
				<div class="fh-right">
					${this._render_risk(s.risk || [])}
					${this._render_throughput(s.throughput_7d || {})}
				</div>
			</div>
		`);

		this._bind_events(s);
	}

	// ── Section renderers ────────────────────────────────────────────

	_render_status_bar(attention, isAllClear, updatedAt) {
		const msgClass = isAllClear ? "is-clear" : "is-urgent";
		return `
			<div class="fh-status">
				<span class="fh-status__msg ${msgClass}">${this.esc(attention)}</span>
				<span class="fh-status__time">${this.esc(this._fmt_time(updatedAt))}</span>
				<button type="button" class="fh-status__btn" data-action="queue">
					${this.esc(__("Action Queue"))}
				</button>
			</div>
		`;
	}

	_render_counts(counts) {
		const cards = counts
			.map(
				(c, i) => `
				<button type="button" class="fh-card" data-count-index="${i}"
				        style="--fh-accent:${this.esc(c.accent || "#2563eb")}">
					<div class="fh-card__label">${this.esc(c.label || "")}</div>
					<div class="fh-card__value ${c.value === 0 ? "is-zero" : ""}">${c.value}</div>
				</button>
			`
			)
			.join("");
		return `<div class="fh-counts">${cards}</div>`;
	}

	_render_focus_queue(queue) {
		const body = queue.length
			? queue
					.map((row, i) => {
						const band = row.urgency_band || "active";
						const tag =
							band !== "active"
								? `<span class="fh-tag band-${band}">${this.esc(this._band_label(band))}</span>`
								: "";
						const priority = row.is_high_priority
							? `<span class="fh-priority">${this.esc(row.priority || "")}</span>`
							: "";
						const dueLabel = row.due_label
							? `<span>${this.esc(row.due_label)}</span>`
							: "";
						return `
						<button type="button" class="fh-item fh-band-${band}" data-queue-index="${i}">
							<div class="fh-item__title">${this.esc(row.title || row.name || "")}</div>
							<div class="fh-item__meta">${tag}${priority}${dueLabel}</div>
						</button>
					`;
					})
					.join("")
			: `<div class="fh-empty is-clear">${this.esc(
					__("All clear. Nothing needs attention right now.")
			  )}</div>`;

		return `
			<div class="fh-panel">
				<div class="fh-panel__head">
					<h2 class="fh-panel__title">${this.esc(__("Focus Queue"))}</h2>
					<p class="fh-panel__sub">${this.esc(__("Sorted by urgency, click to open"))}</p>
				</div>
				<div class="fh-queue">${body}</div>
			</div>
		`;
	}

	_render_risk(risk) {
		const rows = risk
			.map(
				(r, i) => `
				<div class="fh-risk-row" data-risk-index="${i}" role="button">
					<span class="fh-risk-row__label">${this.esc(r.label || "")}</span>
					<span class="fh-risk-row__value ${r.value === 0 ? "is-zero" : ""}">${r.value}</span>
					<span class="fh-risk-row__arrow">›</span>
				</div>
			`
			)
			.join('<hr class="fh-divider">');

		return `
			<div class="fh-panel">
				<div class="fh-panel__head">
					<h2 class="fh-panel__title">${this.esc(__("Risk Signals"))}</h2>
				</div>
				<div class="fh-risk">${rows}</div>
			</div>
		`;
	}

	_render_throughput(t) {
		const created = t.created || 0;
		const closed = t.closed || 0;
		const net = t.net !== undefined ? t.net : closed - created;
		const maxVal = Math.max(created, closed, 1);
		const createdPct = Math.round((created / maxVal) * 100);
		const closedPct = Math.round((closed / maxVal) * 100);

		let netClass, netText;
		if (net > 0) {
			netClass = "is-behind";
			netText = __("Net +{0}, falling behind", [net]);
		} else if (net < 0) {
			netClass = "is-ahead";
			netText = __("Net {0}, keeping up", [net]);
		} else {
			netClass = "is-neutral";
			netText = __("Net 0, balanced");
		}

		return `
			<div class="fh-panel">
				<div class="fh-panel__head">
					<h2 class="fh-panel__title">${this.esc(__("Last 7 Days"))}</h2>
				</div>
				<div class="fh-throughput">
					<div class="fh-trow">
						<span class="fh-trow__label">${this.esc(__("Created"))}</span>
						<div class="fh-trow__bar-wrap">
							<div class="fh-trow__bar is-created" style="width:${createdPct}%"></div>
						</div>
						<span class="fh-trow__count">${created}</span>
					</div>
					<div class="fh-trow">
						<span class="fh-trow__label">${this.esc(__("Closed"))}</span>
						<div class="fh-trow__bar-wrap">
							<div class="fh-trow__bar is-closed" style="width:${closedPct}%"></div>
						</div>
						<span class="fh-trow__count">${closed}</span>
					</div>
					<div class="fh-net ${netClass}">${this.esc(netText)}</div>
				</div>
			</div>
		`;
	}

	// ── Event binding ─────────────────────────────────────────────────

	_bind_events(s) {
		const counts = s.counts || [];
		const queue = s.focus_queue || [];
		const risk = s.risk || [];

		this.$root.find("[data-action='queue']").on("click", () => this.open_action_queue());

		this.$root.find("[data-count-index]").each((_, el) => {
			const card = counts[parseInt($(el).attr("data-count-index"), 10)];
			if (card) $(el).on("click", () => this._navigate(card));
		});

		this.$root.find("[data-queue-index]").each((_, el) => {
			const row = queue[parseInt($(el).attr("data-queue-index"), 10)];
			if (row?.name) $(el).on("click", () => frappe.set_route("Form", "ToDo", row.name));
		});

		this.$root.find("[data-risk-index]").each((_, el) => {
			const signal = risk[parseInt($(el).attr("data-risk-index"), 10)];
			if (signal) $(el).on("click", () => this._navigate(signal));
		});
	}

	// ── Helpers ──────────────────────────────────────────────────────

	_navigate(item) {
		if (!item || !Array.isArray(item.route) || !item.route.length) return;
		frappe.route_options = item.route_options || {};
		frappe.set_route(...item.route);
	}

	open_action_queue() {
		frappe.route_options = { status: ["Open", "In Progress"] };
		frappe.set_route("query-report", "ToDo Action Queue");
	}

	_band_label(band) {
		return { overdue: __("Overdue"), due_today: __("Today"), stale: __("Stale"), due_soon: __("Soon") }[band] || band;
	}

	_fmt_time(value) {
		if (!value) return __("Just now");
		try {
			return __("Updated {0}", [frappe.datetime.str_to_user(value)]);
		} catch {
			return __("Just now");
		}
	}

	esc(value) {
		return frappe.utils.escape_html(String(value ?? ""));
	}
};
