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
		this._active_tab = null;

		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Flow Hub"),
			single_column: true,
		});

		this.page.set_primary_action(__("Refresh"), () => this.refresh({ force: true }), "refresh");
		this.page.set_secondary_action(__("New ToDo"), () => frappe.new_doc("ToDo"), "add");
		this.page.add_menu_item(__("Open ToDo Explorer"), () => this.open_action_queue());
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
				flex: 0 0 auto;
				font-size: 0.88rem;
				font-weight: 600;
				color: var(--text-color);
			}
			.fh-status__msg.is-clear  { color: #64748b; }
			.fh-status__msg.is-ahead  { color: #047857; font-weight: 700; }
			.fh-status__time {
				flex-shrink: 0;
				font-size: 0.72rem;
				color: var(--text-muted);
			}
			.fh-status__time .frappe-timestamp { pointer-events: none; }
			.fh-status__btn {
				border: 1px solid var(--border-color);
				background: var(--fg-color);
				color: var(--text-color);
				padding: 0.28rem 0.6rem;
				border-radius: 7px;
				font-size: 0.76rem;
				font-weight: 500;
				cursor: pointer;
				transition: background 130ms;
				white-space: nowrap;
				flex-shrink: 0;
			}
			.fh-status__btn:hover { background: var(--bg-color); }

			/* ── Count chips (inline in status bar) ─────────────── */
			.fh-chips {
				display: flex;
				align-items: center;
				justify-content: center;
				gap: 0.3rem;
				flex: 1 1 auto;
				flex-wrap: wrap;
				min-width: 0;
			}
			.fh-chip {
				display: flex;
				align-items: baseline;
				gap: 0.25rem;
				padding: 0.22rem 0.5rem;
				border-radius: 6px;
				border: 1px solid var(--border-color);
				border-top: 3px solid var(--fh-accent, var(--border-color));
				background: var(--fg-color);
				cursor: pointer;
				transition: background 130ms;
				white-space: nowrap;
			}
			.fh-chip:hover { background: var(--bg-color); }
			.fh-chip.is-active {
				background: var(--bg-color);
				border-top-width: 4px;
				box-shadow: 0 2px 6px rgba(0,0,0,0.07);
			}
			.fh-chip.is-active .fh-chip__label { color: var(--fh-accent, var(--text-color)); }
			.fh-chip--label-only .fh-chip__label { font-weight: 600; }
			.fh-chip__value {
				font-size: 0.76rem;
				font-weight: 700;
				color: var(--fh-accent, var(--text-color));
				line-height: 1;
			}
			.fh-chip__value.is-zero { color: var(--text-muted); }
			.fh-chip__label {
				font-size: 0.76rem;
				font-weight: 500;
				color: var(--text-muted);
			}

			/* ── Two-column body ────────────────────────────────── */
			.fh-body {
				display: grid;
				grid-template-columns: 1.3fr 1fr;
				gap: 0.65rem;
			}
			.fh-right { display: flex; flex-direction: column; gap: 0.65rem; }

			/* ── Shared panel chrome ────────────────────────────── */
			.fh-panel {
				background: var(--fg-color);
				border: 1px solid var(--border-color);
				border-radius: 10px;
			}
			.fh-panel__head {
				display: flex;
				align-items: baseline;
				flex-wrap: wrap;
				gap: 0 0.5rem;
				padding: 0.65rem 0.75rem 0.35rem;
			}
			.fh-panel__title {
				font-size: 0.69rem;
				font-weight: 700;
				color: var(--text-muted);
				text-transform: uppercase;
				letter-spacing: 0.07em;
				margin: 0;
			}
			.fh-panel__sub {
				font-size: 0.71rem;
				color: var(--text-muted);
				margin: 0 0 0 auto;
			}

			/* ── Focus queue ────────────────────────────────────── */
			.fh-queue { padding: 0 0.5rem 0.6rem; }
			.fh-item {
				display: flex;
				align-items: center;
				gap: 0.6rem;
				width: 100%;
				text-align: left;
				padding: 0.5rem 0.6rem;
				margin-bottom: 0.35rem;
				border-radius: 8px;
				border: 1px solid var(--border-color);
				border-left: 4px solid var(--fh-band-color, var(--border-color));
				background: var(--fg-color);
				cursor: pointer;
				transition: background 130ms;
			}
			.fh-item:hover { background: var(--bg-color); }
			.fh-item:last-child { margin-bottom: 0; }
			.fh-item__body {
				flex: 1;
				min-width: 0;
			}
			.fh-item__title {
				font-size: 0.83rem;
				font-weight: 600;
				color: var(--text-color);
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
				color: var(--text-muted);
			}

			/* Urgency band accent (left border colour) */
			.fh-band-overdue   { --fh-band-color: #ef4444; }
			.fh-band-due_today { --fh-band-color: #f97316; }
			.fh-band-stale     { --fh-band-color: #7c3aed; }
			.fh-band-due_soon  { --fh-band-color: #2563eb; }

			/* Urgency tag pill — keep hardcoded, these are semantic colours */
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

			/* Priority pill — semantic amber, keep hardcoded */
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

			/* ── Priority icon (sits left of the band border) ───────── */
			.fh-item-wrap {
				display: flex;
				align-items: stretch;
				gap: 0.3rem;
				margin-bottom: 0.35rem;
			}
			.fh-item-wrap:last-child { margin-bottom: 0; }
			.fh-item-wrap .fh-item  { flex: 1; margin-bottom: 0; }
			.fh-prio-btn {
				display: flex;
				align-items: center;
				justify-content: center;
				width: 18px;
				flex-shrink: 0;
				border: none;
				background: none;
				font-size: 0.82rem;
				font-weight: 800;
				cursor: pointer;
				padding: 0;
				line-height: 1;
				border-radius: 4px;
				transition: background 120ms;
			}
			.fh-prio-btn:hover { background: #f1f5f9; }

			/* Priority dropdown */
			.fh-prio-drop {
				position: fixed;
				z-index: 2000;
				background: #ffffff;
				border: 1px solid #e2e8f0;
				border-radius: 8px;
				box-shadow: 0 4px 16px rgba(0,0,0,0.12);
				min-width: 130px;
				padding: 0.25rem;
				display: none;
			}
			.fh-prio-drop.is-open { display: block; }
			.fh-prio-drop__opt {
				display: flex;
				align-items: center;
				gap: 0.4rem;
				padding: 0.35rem 0.55rem;
				border-radius: 5px;
				cursor: pointer;
				font-size: 0.78rem;
				font-weight: 500;
				color: #0f172a;
				transition: background 100ms;
			}
			.fh-prio-drop__opt:hover { background: #f8fafc; }
			.fh-prio-drop__icon {
				font-size: 0.75rem;
				font-weight: 800;
				width: 14px;
				text-align: center;
				flex-shrink: 0;
			}

			/* ── Tooltip (data-tip="…") ─────────────────────────── */
			[data-tip] { position: relative; }
			[data-tip]::before {
				content: "";
				position: absolute;
				top: calc(100% + 1px);
				left: 50%;
				transform: translateX(-50%);
				border: 5px solid transparent;
				border-bottom-color: #1e293b;
				pointer-events: none;
				opacity: 0;
				transition: opacity 0.15s ease;
				z-index: 1001;
			}
			[data-tip]::after {
				content: attr(data-tip);
				position: absolute;
				top: calc(100% + 11px);
				left: 50%;
				transform: translateX(-50%);
				white-space: nowrap;
				background: #1e293b;
				color: #f8fafc;
				font-size: 0.72rem;
				font-weight: 500;
				padding: 0.25rem 0.55rem;
				border-radius: 5px;
				pointer-events: none;
				opacity: 0;
				transition: opacity 0.15s ease;
				z-index: 1000;
				box-shadow: 0 2px 6px rgba(0,0,0,0.25);
			}
			[data-tip]:hover::before,
			[data-tip]:hover::after { opacity: 1; }

			.fh-empty {
				padding: 1.2rem 0.75rem;
				font-size: 0.8rem;
				color: #94a3b8;
				text-align: center;
			}
			.fh-empty.is-clear { color: #047857; font-weight: 600; }

			/* ── Assignee avatars ───────────────────────────────── */
			.fh-avatars {
				display: flex;
				align-items: center;
				flex-shrink: 0;
			}
			.fh-avatars [data-tip] {
				display: inline-flex;
				margin-left: -6px;
			}
			.fh-avatars [data-tip]:first-child { margin-left: 0; }
			.fh-avatar {
				width: 22px;
				height: 22px;
				border-radius: 50%;
				border: 2px solid #ffffff;
				font-size: 0.6rem;
				font-weight: 700;
				display: flex;
				align-items: center;
				justify-content: center;
				overflow: hidden;
				flex-shrink: 0;
				color: #ffffff;
				text-transform: uppercase;
			}
			.fh-avatar img { width: 100%; height: 100%; object-fit: cover; }
			.fh-avatar-more {
				width: 22px;
				height: 22px;
				border-radius: 50%;
				border: 2px solid #ffffff;
				margin-left: -6px;
				font-size: 0.58rem;
				font-weight: 700;
				display: flex;
				align-items: center;
				justify-content: center;
				background: #e2e8f0;
				color: #475569;
				flex-shrink: 0;
			}

			/* ── Due date button ────────────────────────────────── */
			.fh-due-btn {
				cursor: pointer;
				border-radius: 3px;
				padding: 0.05rem 0.15rem;
				margin: -0.05rem -0.15rem;
				transition: background 120ms;
				white-space: nowrap;
			}
			.fh-due-btn:hover { background: #f1f5f9; }
			.fh-due-btn--empty {
				color: #cbd5e1;
				font-size: 0.68rem;
			}
			.fh-due-btn--empty:hover { color: #94a3b8; background: #f1f5f9; }

			/* Due date popover */
			.fh-due-pop {
				position: fixed;
				z-index: 2000;
				background: #ffffff;
				border: 1px solid #e2e8f0;
				border-radius: 8px;
				box-shadow: 0 4px 16px rgba(0,0,0,0.12);
				width: 232px;
				padding: 0;
				overflow: hidden;
				display: none;
			}
			.fh-due-pop.is-open { display: block; }

			/* Inline calendar */
			.fh-cal { padding: 0.5rem 0.5rem 0.35rem; }
			.fh-cal__nav {
				display: flex;
				align-items: center;
				justify-content: space-between;
				margin-bottom: 0.4rem;
			}
			.fh-cal__nav-btn {
				background: none;
				border: none;
				cursor: pointer;
				font-size: 1rem;
				line-height: 1;
				padding: 0.15rem 0.35rem;
				border-radius: 4px;
				color: #475569;
				transition: background 100ms;
			}
			.fh-cal__nav-btn:hover { background: #f1f5f9; }
			.fh-cal__month { font-size: 0.8rem; font-weight: 600; color: #0f172a; }
			.fh-cal__grid {
				display: grid;
				grid-template-columns: repeat(7, 1fr);
				gap: 1px;
			}
			.fh-cal__dow {
				text-align: center;
				font-size: 0.62rem;
				font-weight: 600;
				color: #94a3b8;
				padding: 0.15rem 0 0.25rem;
			}
			.fh-cal__day {
				text-align: center;
				font-size: 0.75rem;
				padding: 0.22rem 0;
				border-radius: 4px;
				cursor: pointer;
				color: #0f172a;
				transition: background 100ms;
			}
			.fh-cal__day:hover { background: #f1f5f9; }
			.fh-cal__day.is-other { color: #cbd5e1; cursor: default; }
			.fh-cal__day.is-other:hover { background: none; }
			.fh-cal__day.is-today { font-weight: 700; color: #2563eb; }
			.fh-cal__day.is-selected { background: #2563eb !important; color: #fff !important; font-weight: 600; }

			/* Shortcuts strip */
			.fh-due-pop__shortcuts {
				border-top: 1px solid #f1f5f9;
				padding: 0.25rem;
				display: grid;
				grid-template-columns: 1fr 1fr;
				gap: 0.1rem;
			}
			.fh-due-pop__short {
				display: flex;
				align-items: center;
				justify-content: space-between;
				padding: 0.3rem 0.45rem;
				border-radius: 5px;
				cursor: pointer;
				font-size: 0.75rem;
				font-weight: 500;
				color: #0f172a;
				transition: background 100ms;
				white-space: nowrap;
			}
			.fh-due-pop__short:hover { background: #f8fafc; }
			.fh-due-pop__short-day { color: #94a3b8; font-size: 0.68rem; margin-left: 0.25rem; }
			.fh-due-pop__clear {
				grid-column: 1 / -1;
				display: flex;
				align-items: center;
				justify-content: center;
				padding: 0.3rem 0.45rem;
				margin-top: 0.05rem;
				border-radius: 5px;
				cursor: pointer;
				font-size: 0.75rem;
				font-weight: 500;
				color: #94a3b8;
				transition: background 100ms;
			}
			.fh-due-pop__clear:hover { background: #fff1f2; color: #ef4444; }

			/* ── Add allocatee button ──────────────────────────── */
			.fh-add-alloc {
				display: inline-flex;
				align-items: center;
				justify-content: center;
				width: 26px;
				height: 26px;
				border-radius: 50%;
				border: 2px solid #ffffff;
				background: #e2e8f0;
				color: #94a3b8;
				cursor: pointer;
				transition: background 130ms, color 130ms;
				flex-shrink: 0;
				padding: 0;
			}
			.fh-add-alloc:not(.fh-avatars):hover {
				background: #cbd5e1;
				color: #64748b;
			}
			.fh-add-alloc svg { pointer-events: none; }

			/* Add allocatee popover */
			.fh-alloc-pop {
				position: fixed;
				z-index: 2000;
				background: #ffffff;
				border: 1px solid #e2e8f0;
				border-radius: 8px;
				box-shadow: 0 4px 16px rgba(0,0,0,0.12);
				width: 200px;
				padding: 0.35rem;
				display: none;
			}
			.fh-alloc-pop.is-open { display: block; }
			.fh-alloc-pop__input {
				width: 100%;
				border: 1px solid #e2e8f0;
				border-radius: 5px;
				padding: 0.3rem 0.5rem;
				font-size: 0.78rem;
				outline: none;
				box-sizing: border-box;
			}
			.fh-alloc-pop__input:focus { border-color: #94a3b8; }
			.fh-alloc-pop__results { margin-top: 0.25rem; }
			.fh-alloc-pop__opt {
				display: flex;
				align-items: center;
				gap: 0.4rem;
				padding: 0.32rem 0.45rem;
				border-radius: 5px;
				cursor: pointer;
				font-size: 0.78rem;
				color: #0f172a;
				transition: background 100ms;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
			}
			.fh-alloc-pop__opt:hover { background: #f8fafc; }
			.fh-alloc-pop__empty {
				padding: 0.4rem 0.45rem;
				font-size: 0.75rem;
				color: #94a3b8;
				text-align: center;
			}
			.fh-alloc-pop__current-row { display: flex; align-items: center; }
			.fh-alloc-pop__remove {
				flex-shrink: 0;
				padding: 0 0.2rem;
				color: #94a3b8;
				font-size: 0.85rem;
				line-height: 1;
				cursor: pointer;
			}
			.fh-alloc-pop__remove:hover { color: #ef4444; }
			.fh-avatars.fh-add-alloc { cursor: pointer; }

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
		const tab = this._active_tab;
		let body;
		if (tab === "throughput") {
			body = this._render_throughput(s.throughput_7d || {});
		} else if (tab === "risk") {
			body = this._render_risk(s.risk || []);
		} else {
			body = `<div class="fh-body">
				${this._render_focus_queue(s.focus_queue || [])}
				<div class="fh-right">
					${this._render_risk(s.risk || [])}
					${this._render_throughput(s.throughput_7d || {})}
				</div>
			</div>`;
		}
		this.$root.html(`
			${this._render_status_bar(s.attention || "", s.updated_at, s.counts || [])}
			${body}
		`);
		this._bind_events(s);
	}

	// ── Section renderers ────────────────────────────────────────────

	_render_status_bar(attention, updatedAt, counts) {
		const msgClass = attention.startsWith("Welcome") ? "is-clear" : "is-ahead";
		const chips = (counts || [])
			.map(c => {
				const isActive = this._active_tab === c.key;
				return `<button type="button" class="fh-chip ${isActive ? "is-active" : ""}"
					data-chip-key="${this.esc(c.key)}"
					style="--fh-accent:${this.esc(c.accent || "var(--primary)")}">
					<span class="fh-chip__value ${c.value === 0 ? "is-zero" : ""}">${c.value}</span>
					<span class="fh-chip__label">${this.esc(c.label || "")}</span>
				</button>`;
			})
			.join("");
		const isRiskActive = this._active_tab === "risk";
		return `
			<div class="fh-status">
				<span class="fh-status__msg ${msgClass}">${this.esc(attention)}</span>
				<div class="fh-chips">
					${chips}
					<button type="button" class="fh-chip fh-chip--label-only ${isRiskActive ? "is-active" : ""}"
						data-chip-key="risk" style="--fh-accent:#7c3aed">
						<span class="fh-chip__label">${this.esc(__("Risk Signals"))}</span>
					</button>
					<button type="button" class="fh-chip fh-chip--label-only ${this._active_tab === "throughput" ? "is-active" : ""}"
						data-chip-key="throughput" style="--fh-accent:#059669">
						<span class="fh-chip__label">${this.esc(__("Last 7 Days"))}</span>
					</button>
					<button type="button" class="fh-status__btn" data-action="queue">
						${this.esc(__("Action Queue"))}
					</button>
				</div>
				<span class="fh-status__time">${this._fmt_time(updatedAt)}</span>
			</div>
		`;
	}

	_render_focus_queue(queue) {
		const body = queue.length
			? queue
					.map((row, i) => {
						const band = row.urgency_band || "active";
						const dueTooltip = row.due_date
							? new Date(row.due_date + "T00:00:00").toLocaleDateString(undefined, {
								weekday: "short", month: "short", day: "numeric",
							  })
							: "";
						const dueLabel = row.due_label
							? `<span role="button" class="fh-due-btn" data-due-todo="${this.esc(row.name)}" data-due-date="${this.esc(row.due_date || '')}"${dueTooltip ? ` data-tip="${this.esc(dueTooltip)}"` : ""}>${this.esc(row.due_label)}</span>`
							: `<span role="button" class="fh-due-btn fh-due-btn--empty" data-due-todo="${this.esc(row.name)}" data-due-date="" title="${this.esc(__('Set due date'))}">📅</span>`;
						const avatars = this._render_avatars(row.assignees, row.name);
						const pc = this._prio_config(row.priority);
						const prioTip = this.esc(row.priority || __("Priority"));
						return `
						<div class="fh-item-wrap">
							<button type="button" class="fh-prio-btn" data-tip="${prioTip}" data-prio-index="${i}" data-todo-name="${this.esc(row.name)}" style="color:${pc.color}" title="">${pc.icon}</button>
							<button type="button" class="fh-item fh-band-${band}" data-queue-index="${i}">
								<div class="fh-item__body">
									<div class="fh-item__title">${this.esc(row.title || row.name || "")}</div>
									<div class="fh-item__meta">${dueLabel}</div>
								</div>
								${avatars}
							</button>
						</div>
					`;
					})
					.join("")
			: `<div class="fh-empty is-clear">${this.esc(
					__("All clear.")
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

		this.$root.find("[data-chip-key]").on("click", (e) => {
			const key = $(e.currentTarget).attr("data-chip-key");
			this._active_tab = (this._active_tab === key) ? null : key;
			this.render();
		});

		this.$root.find("[data-queue-index]").each((_, el) => {
			const row = queue[parseInt($(el).attr("data-queue-index"), 10)];
			if (row?.name) $(el).on("click", () => frappe.set_route("Form", "ToDo", row.name));
		});

		this.$root.find("[data-prio-index]").on("click", (e) => {
			e.stopPropagation();
			this._open_prio_dropdown(e.currentTarget);
		});

		this.$root.find("[data-add-alloc]").on("click", (e) => {
			e.stopPropagation();
			this._open_allocatee_popover(e.currentTarget);
		});

		this.$root.find("[data-due-todo]").on("click", (e) => {
			e.stopPropagation();
			this._open_due_date_popover(e.currentTarget);
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
		frappe.route_options = { status: ["in", "Open,In Progress"] };
		frappe.set_route("List", "ToDo", "List");
	}

	_render_avatars(assignees, todoName) {
		const nameAttr = `data-add-alloc="${this.esc(todoName || "")}"`;
		if (!assignees || !assignees.length) {
			return `<span role="button" tabindex="0" class="fh-add-alloc" data-tip="${this.esc(__("Add Allocatee"))}" ${nameAttr}>
				<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
					<path d="M12 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10zm0 2c-5.33 0-8 2.67-8 4v1h16v-1c0-1.33-2.67-4-8-4z"/>
				</svg>
			</span>`;
		}
		const PALETTE = ["#2563eb","#059669","#d97706","#7c3aed","#db2777","#0891b2","#65a30d","#dc2626"];
		const _color = (user) => {
			let h = 0;
			for (let i = 0; i < user.length; i++) h = (h * 31 + user.charCodeAt(i)) >>> 0;
			return PALETTE[h % PALETTE.length];
		};
		const MAX = 3;
		const shown = assignees.slice(0, MAX);
		const extra = assignees.length - MAX;
		const chips = shown.map(a => {
			if (a.image) {
				return `<span data-tip="${this.esc(a.full_name)}"><span class="fh-avatar"><img src="${this.esc(a.image)}" alt="${this.esc(a.initials)}"></span></span>`;
			}
			return `<span data-tip="${this.esc(a.full_name)}"><span class="fh-avatar" style="background:${_color(a.user)}">${this.esc(a.initials)}</span></span>`;
		}).join("");
		const more = extra > 0 ? `<span class="fh-avatar-more">+${extra}</span>` : "";
		return `<span role="button" tabindex="0" class="fh-avatars fh-add-alloc" ${nameAttr}>${chips}${more}</span>`;
	}

	_open_allocatee_popover(btn) {
		const todoName = $(btn).attr("data-add-alloc");
		const queueRow = (this.snapshot.focus_queue || []).find(r => r.name === todoName);
		const current = (queueRow && queueRow.assignees) || [];

		let $pop = $("#fh-alloc-pop");
		if (!$pop.length) {
			$pop = $(`<div id="fh-alloc-pop" class="fh-alloc-pop">
				<div class="fh-alloc-pop__current"></div>
				<input type="text" class="fh-alloc-pop__input" placeholder="${__("Add user…")}">
				<div class="fh-alloc-pop__results"></div>
			</div>`).appendTo(document.body);

			$pop.on("input", ".fh-alloc-pop__input", (e) => {
				const name = $($pop.data("active-btn")).attr("data-add-alloc");
				const row = (this.snapshot.focus_queue || []).find(r => r.name === name);
				const existing = new Set(((row && row.assignees) || []).map(a => a.user));
				this._search_allocatee_users($(e.target).val(), $pop, existing);
			});

			$pop.on("click", ".fh-alloc-pop__opt[data-user]", (e) => {
				e.stopPropagation();
				const user = $(e.currentTarget).attr("data-user");
				const name = $($pop.data("active-btn")).attr("data-add-alloc");
				if (!user || !name) return;
				$pop.removeClass("is-open");
				frappe.call({
					method: "opero.todo_dashboard.add_todo_allocatee",
					args: { todo_name: name, user },
					callback: () => this.refresh({ force: true }),
				});
			});

			$pop.on("click", ".fh-alloc-pop__remove", (e) => {
				e.stopPropagation();
				const user = $(e.currentTarget).attr("data-user");
				const name = $($pop.data("active-btn")).attr("data-add-alloc");
				if (!user || !name) return;
				$pop.removeClass("is-open");
				frappe.call({
					method: "opero.todo_dashboard.remove_todo_allocatee",
					args: { todo_name: name, user },
					callback: () => this.refresh({ force: true }),
				});
			});
		}

		if ($pop.hasClass("is-open") && $pop.data("active-btn") === btn) {
			$pop.removeClass("is-open");
			return;
		}

		// Render current allocatees with remove buttons
		const $curr = $pop.find(".fh-alloc-pop__current").empty();
		if (current.length) {
			current.forEach(a => {
				$curr.append(`<div class="fh-alloc-pop__opt fh-alloc-pop__current-row">
					<span style="flex:1;overflow:hidden;text-overflow:ellipsis">${this.esc(a.full_name || a.user)}</span>
					<span class="fh-alloc-pop__remove" data-user="${this.esc(a.user)}" title="${__("Remove")}">×</span>
				</div>`);
			});
			$curr.append(`<hr style="margin:0.25rem 0;border:none;border-top:1px solid #f1f5f9">`);
		}

		const rect = btn.getBoundingClientRect();
		$pop.css({ top: rect.bottom + 4, left: Math.max(4, rect.right - 200) });
		$pop.data("active-btn", btn).addClass("is-open");
		$pop.find(".fh-alloc-pop__input").val("").focus();
		const existing = new Set(current.map(a => a.user));
		this._search_allocatee_users("", $pop, existing);

		setTimeout(() => {
			$(document).one("click.fh-alloc", () => $pop.removeClass("is-open"));
		}, 0);
	}

	_search_allocatee_users(query, $pop, excludeSet = new Set()) {
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "User",
				filters: [
					["enabled", "=", 1],
					["user_type", "=", "System User"],
					...(query ? [["full_name", "like", `%${query}%`]] : []),
				],
				fields: ["name", "full_name"],
				limit_page_length: 8,
			},
			callback: (r) => {
				const users = (r.message || []).filter(u => !excludeSet.has(u.name));
				const $results = $pop.find(".fh-alloc-pop__results").empty();
				if (!users.length) {
					$results.html(`<div class="fh-alloc-pop__empty">${__("No users found")}</div>`);
					return;
				}
				users.forEach(u => {
					$results.append(`<div class="fh-alloc-pop__opt" data-user="${this.esc(u.name)}">${this.esc(u.full_name || u.name)}</div>`);
				});
			},
		});
	}

	_prio_config(priority) {
		const map = {
			"High":   { icon: "↑", color: "#d97706" },
			"Medium": { icon: "↑", color: "#94a3b8" },
			"Low":    { icon: "↓", color: "#3b82f6" },
		};
		return map[priority] || { icon: "↑", color: "#cbd5e1" };
	}

	_open_prio_dropdown(btn) {
		const PRIORITIES = [
			{ value: "High",   label: __("High"),   icon: "↑", color: "#d97706" },
			{ value: "Medium", label: __("Medium"), icon: "↑", color: "#94a3b8" },
			{ value: "Low",    label: __("Low"),    icon: "↓", color: "#3b82f6" },
		];

		let $drop = $("#fh-prio-drop");
		if (!$drop.length) {
			$drop = $(`<div id="fh-prio-drop" class="fh-prio-drop">
				${PRIORITIES.map(p => `
					<div class="fh-prio-drop__opt" data-prio-value="${p.value}">
						<span class="fh-prio-drop__icon" style="color:${p.color}">${p.icon}</span>
						<span>${p.label}</span>
					</div>
				`).join("")}
			</div>`).appendTo(document.body);

			$drop.on("click", ".fh-prio-drop__opt", (e) => {
				e.stopPropagation();
				const newPrio = $(e.currentTarget).attr("data-prio-value");
				const $btn = $drop.data("active-btn");
				$drop.removeClass("is-open");
				if (!$btn) return;
				const todoName = $($btn).attr("data-todo-name");
				frappe.call({
					method: "frappe.client.set_value",
					args: { doctype: "ToDo", name: todoName, fieldname: "priority", value: newPrio },
					callback: () => this.refresh({ force: true }),
				});
			});
		}

		if ($drop.hasClass("is-open") && $drop.data("active-btn") === btn) {
			$drop.removeClass("is-open");
			return;
		}

		const rect = btn.getBoundingClientRect();
		$drop.css({ top: rect.bottom + 4, left: rect.left });
		$drop.data("active-btn", btn).addClass("is-open");

		setTimeout(() => {
			$(document).one("click.fh-prio", () => $drop.removeClass("is-open"));
		}, 0);
	}

	_open_due_date_popover(btn) {
		const todoName = $(btn).attr("data-due-todo");
		const currentDate = $(btn).attr("data-due-date") || "";

		const SHORTCUTS = [
			{ label: __("Today"),    days: 0 },
			{ label: __("Tomorrow"), days: 1 },
		];

		let $pop = $("#fh-due-pop");
		if (!$pop.length) {
			$pop = $(`<div id="fh-due-pop" class="fh-due-pop">
				<div class="fh-due-pop__cal"></div>
				<div class="fh-due-pop__shortcuts"></div>
			</div>`).appendTo(document.body);

			$pop.on("click", "[data-cal-nav]", (e) => {
				e.stopPropagation();
				const delta = parseInt($(e.currentTarget).attr("data-cal-nav"), 10);
				let { cy, cm } = $pop.data("cal-state") || {};
				cm += delta;
				if (cm > 11) { cm = 0; cy++; }
				if (cm < 0)  { cm = 11; cy--; }
				$pop.data("cal-state", { cy, cm });
				const sel = $pop.data("active-date") || "";
				$pop.find(".fh-due-pop__cal").html(this._cal_html(cy, cm, sel));
			});

			$pop.on("click", "[data-cal-date]", (e) => {
				e.stopPropagation();
				const dateStr = $(e.currentTarget).attr("data-cal-date");
				const name = $pop.data("active-todo");
				$pop.removeClass("is-open");
				if (name && dateStr) this._save_due_date(name, dateStr);
			});

			$pop.on("click", "[data-due-days]", (e) => {
				e.stopPropagation();
				const name = $pop.data("active-todo");
				const days = parseInt($(e.currentTarget).attr("data-due-days"), 10);
				$pop.removeClass("is-open");
				if (!name) return;
				this._save_due_date(name, frappe.datetime.add_days(frappe.datetime.get_today(), days));
			});

			$pop.on("click", "[data-due-shortcut='clear']", (e) => {
				e.stopPropagation();
				const name = $pop.data("active-todo");
				$pop.removeClass("is-open");
				if (name) this._save_due_date(name, "");
			});
		}

		if ($pop.hasClass("is-open") && $pop.data("active-todo") === todoName) {
			$pop.removeClass("is-open");
			return;
		}

		// Determine calendar view month
		const today = frappe.datetime.get_today();
		const viewDate = currentDate || today;
		const [vy, vm] = viewDate.split("-").map(Number);
		const cy = vy, cm = vm - 1;

		$pop.data({ "active-todo": todoName, "active-date": currentDate, "cal-state": { cy, cm } });
		$pop.find(".fh-due-pop__cal").html(this._cal_html(cy, cm, currentDate));

		// Build shortcuts
		const $sc = $pop.find(".fh-due-pop__shortcuts").empty();
		SHORTCUTS.forEach(s => {
			const d = frappe.datetime.add_days(today, s.days);
			const dayName = new Date(d + "T00:00:00").toLocaleDateString(undefined, { weekday: "short" });
			$sc.append(`<div class="fh-due-pop__short" data-due-days="${s.days}">
				${this.esc(s.label)}<span class="fh-due-pop__short-day">${this.esc(dayName)}</span>
			</div>`);
		});
		if (currentDate) {
			$sc.append(`<div class="fh-due-pop__clear" data-due-shortcut="clear">${__("Clear")}</div>`);
		}

		const rect = btn.getBoundingClientRect();
		const left = Math.min(Math.max(4, rect.left), window.innerWidth - 240);
		$pop.css({ top: rect.bottom + 4, left });
		$pop.addClass("is-open");

		setTimeout(() => {
			$(document).one("click.fh-due", () => $pop.removeClass("is-open"));
		}, 0);
	}

	_cal_html(year, month, selectedDate) {
		const DOWS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
		const today = frappe.datetime.get_today();
		const firstDay = new Date(year, month, 1).getDay();
		const daysInMonth = new Date(year, month + 1, 0).getDate();
		const daysInPrev  = new Date(year, month, 0).getDate();
		const monthLabel  = new Date(year, month, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" });

		let cells = "";
		// trailing days from prev month
		for (let i = firstDay - 1; i >= 0; i--) {
			cells += `<span class="fh-cal__day is-other">${daysInPrev - i}</span>`;
		}
		// current month days
		for (let d = 1; d <= daysInMonth; d++) {
			const ds = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
			let cls = "fh-cal__day";
			if (ds === today) cls += " is-today";
			if (ds === selectedDate) cls += " is-selected";
			cells += `<span class="${cls}" data-cal-date="${ds}">${d}</span>`;
		}
		// leading days from next month
		const total = Math.ceil((firstDay + daysInMonth) / 7) * 7;
		for (let d = 1; d <= total - firstDay - daysInMonth; d++) {
			cells += `<span class="fh-cal__day is-other">${d}</span>`;
		}

		return `<div class="fh-cal">
			<div class="fh-cal__nav">
				<button class="fh-cal__nav-btn" data-cal-nav="-1">‹</button>
				<span class="fh-cal__month">${this.esc(monthLabel)}</span>
				<button class="fh-cal__nav-btn" data-cal-nav="1">›</button>
			</div>
			<div class="fh-cal__grid">
				${DOWS.map(d => `<span class="fh-cal__dow">${d}</span>`).join("")}
				${cells}
			</div>
		</div>`;
	}

	_save_due_date(todoName, date) {
		frappe.call({
			method: "frappe.client.set_value",
			args: { doctype: "ToDo", name: todoName, fieldname: "date", value: date || "" },
			callback: () => this.refresh({ force: true }),
		});
	}

	_band_label(band) {
		return { overdue: __("Overdue"), due_today: __("Today"), stale: __("Stale"), due_soon: __("Soon") }[band] || band;
	}

	_fmt_time(value) {
		if (!value) return "";
		try {
			const relative = frappe.datetime.comment_when(value);
			const full = new Date(value).toLocaleString(undefined, {
				weekday: "short", month: "short", day: "numeric",
				hour: "2-digit", minute: "2-digit", hour12: false,
			});
			return `<span data-tip="${this.esc(full)}">${__("Updated")} ${relative}</span>`;
		} catch {
			return "";
		}
	}

	esc(value) {
		return frappe.utils.escape_html(String(value ?? ""));
	}
};
