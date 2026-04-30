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
		this._selected_todo = null;

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
		this._init_tooltip();
		$(this.page.main).empty();
		this.$root = $("<div class='fh'></div>").appendTo(this.page.main);
		this.render_loading();
		this.refresh();
	}

	_inject_styles() {
		let style = document.getElementById("fh-styles");
		if (!style) {
			style = document.createElement("style");
			style.id = "fh-styles";
			document.head.appendChild(style);
		}
		style.textContent = `
			.fh {
				padding: 0 0 1rem 0;
				min-height: calc(100vh - 120px);
				background: var(--bg-color);
			}

			/* ── Status bar ─────────────────────────────────────── */
			.fh-status {
				display: flex;
				align-items: stretch;
				height: 44px;
				border-radius: 10px;
				background: var(--fg-color);
				border: 1px solid var(--border-color);
				margin-bottom: 0.65rem;
				overflow: hidden;
			}
			.fh-status__msg {
				display: flex;
				align-items: center;
				flex-shrink: 0;
				padding: 0 0.9rem;
				font-size: 0.82rem;
				font-weight: var(--weight-semibold);
				color: #64748b;
				border-right: 1px solid var(--border-color);
				white-space: nowrap;
			}
			.fh-status__msg.is-ahead { color: #047857; }
			.fh-status__time {
				display: flex;
				align-items: center;
				flex-shrink: 0;
				padding: 0 0.9rem;
				font-size: 0.7rem;
				color: var(--text-muted);
				border-left: 1px solid var(--border-color);
				white-space: nowrap;
			}
			.fh-status__time .frappe-timestamp { pointer-events: none; }

			/* ── Chips ───────────────────────────────────────────── */
			.fh-chips {
				display: flex;
				align-items: stretch;
				flex: 1;
				min-width: 0;
			}
			.fh-chip {
				display: flex;
				align-items: center;
				gap: 0.22rem;
				padding: 0 0.6rem;
				border: none;
				background: transparent;
				cursor: pointer;
				transition: background 120ms;
				white-space: nowrap;
				position: relative;
				color: inherit;
				flex-shrink: 0;
			}
			.fh-chip:hover { background: var(--bg-color); }
			.fh-chip.is-active { background: var(--bg-color); }
			.fh-chip.is-active::before {
				content: "";
				position: absolute;
				bottom: 0;
				left: 0.35rem;
				right: 0.35rem;
				height: 2px;
				background: var(--fh-accent, var(--primary));
				border-radius: 2px 2px 0 0;
			}
			.fh-chip__icon {
				width: 13px;
				height: 13px;
				flex-shrink: 0;
				color: var(--text-muted);
				transition: color 120ms;
			}
			.fh-chip.is-active .fh-chip__icon { color: var(--fh-accent, var(--primary)); }
			.fh-chip__icon.is-accented { color: var(--fh-accent, var(--text-muted)); }
			.fh-chip__value {
				font-size: 0.74rem;
				font-weight: var(--weight-semibold);
				line-height: 1;
				color: var(--text-muted);
				transition: color 120ms;
			}
			.fh-chip__value.is-nonzero { color: var(--fh-accent, var(--text-color)); }
			.fh-chip.is-active .fh-chip__value { color: var(--fh-accent, var(--primary)); }

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
			.fh-panel--queue {
				overflow: hidden;
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
				font-weight: var(--weight-semibold);
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
			.fh-queue { padding: 0; }
			.fh-item {
				display: flex;
				align-items: center;
				gap: 0.6rem;
				width: 100%;
				text-align: left;
				padding: 0.3rem 0;
				margin: 0;
				border-radius: 0;
				border: none;
				border-bottom: 1px solid var(--border-color);
				background: var(--fg-color);
				cursor: pointer;
				transition: background 130ms;
			}
			.fh-item:hover { background: var(--bg-color); }
			.fh-item:last-child { border-bottom: none; }
			.fh-item__body {
				flex: 1;
				min-width: 0;
			}
			.fh-item__title {
				font-size: 0.83rem;
				font-weight: var(--weight-semibold);
				color: var(--text-color);
				line-height: 1.3;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
				margin-bottom: 0.1rem;
			}
			.fh-item__due {
				width: 130px;
				flex-shrink: 0;
				text-align: left;
				font-size: 0.71rem;
				color: var(--text-muted);
			}

			/* ── Queue + detail split ───────────────────────────── */
			.fh-queue-layout {
				display: flex;
				gap: 0;
				align-items: stretch;
				transition: width 280ms ease-in-out, margin 280ms ease-in-out;
				overflow-x: visible;
			}
			.fh-queue-layout > .fh-panel--queue {
				flex: 1;
				min-width: 0;
				border-right: none;
				border-radius: 10px 0 0 10px;
				overflow-y: auto;
			}

			/* ── Detail panel ───────────────────────────────────── */
			.fh-detail {
				width: 420px;
				flex-shrink: 0;
				background: var(--fg-color);
				border: 1px solid var(--border-color);
				border-radius: 0 10px 10px 0;
				overflow-y: auto;
			}
			.fh-detail__bar {
				display: flex;
				align-items: center;
				justify-content: space-between;
				padding: 0.45rem 0.65rem;
				border-bottom: 1px solid #f1f5f9;
			}
			.fh-detail__close {
				border: none;
				background: none;
				cursor: pointer;
				font-size: 1rem;
				line-height: 1;
				color: #94a3b8;
				padding: 0.1rem 0.3rem;
				border-radius: 4px;
			}
			.fh-detail__close:hover { background: #f1f5f9; color: #475569; }
			.fh-detail__open {
				font-size: 0.73rem;
				color: var(--primary);
				text-decoration: none;
			}
			.fh-detail__open:hover { text-decoration: underline; }
			.fh-detail__scroll { padding: 0.75rem; }
			.fh-detail__title {
				font-size: 0.88rem;
				font-weight: var(--weight-semibold);
				color: #0f172a;
				margin: 0 0 0.8rem;
				line-height: 1.45;
			}
			.fh-detail__fields {
				display: flex;
				flex-direction: column;
				gap: 0.45rem;
				margin-bottom: 0.75rem;
			}
			.fh-detail__row {
				display: flex;
				align-items: center;
				gap: 0.5rem;
				font-size: 0.76rem;
			}
			.fh-detail__key {
				width: 72px;
				flex-shrink: 0;
				color: #94a3b8;
				font-weight: var(--weight-medium);
			}
			.fh-detail__val { color: #334155; }
			.fh-detail__desc {
				font-size: 0.76rem;
				color: #475569;
				line-height: 1.55;
				border-top: 1px solid #f1f5f9;
				padding-top: 0.65rem;
			}
			.fh-item.is-selected {
				background: var(--bg-color);
				border-left: 3px solid var(--primary);
				border-right: none;
				border-radius: 0;
			}

			/* Urgency tag pill — keep hardcoded, these are semantic colours */
			.fh-tag {
				padding: 0.11rem 0.34rem;
				border-radius: 4px;
				font-size: 0.65rem;
				font-weight: var(--weight-semibold);
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
				font-weight: var(--weight-semibold);
				text-transform: uppercase;
				letter-spacing: 0.04em;
			}

			/* ── Priority icon (sits left of the band border) ───────── */
			.fh-prio-btn {
				display: inline-flex;
				align-items: center;
				justify-content: center;
				width: 20px;
				flex-shrink: 0;
				background: none;
				font-size: 0.82rem;
				font-weight: var(--weight-semibold);
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
				font-weight: var(--weight-medium);
				color: #0f172a;
				transition: background 100ms;
			}
			.fh-prio-drop__opt:hover { background: #f8fafc; }
			.fh-prio-drop__icon {
				font-size: 0.75rem;
				font-weight: var(--weight-semibold);
				width: 14px;
				text-align: center;
				flex-shrink: 0;
			}

			/* ── Kill any stale CSS pseudo-element tooltips ─────── */
			[data-tip]::before, [data-tip]::after { display: none !important; }

			/* ── Tooltip (positioned by JS, escapes overflow:hidden) */
			.fh-tooltip {
				position: fixed;
				z-index: 9999;
				background: #1e293b;
				color: #f8fafc;
				font-size: 0.72rem;
				font-weight: var(--weight-medium);
				padding: 0.25rem 0.55rem;
				border-radius: 5px;
				pointer-events: none;
				white-space: nowrap;
				box-shadow: 0 2px 6px rgba(0,0,0,0.25);
				opacity: 0;
				transition: opacity 0.15s ease;
			}
			.fh-tooltip.is-visible { opacity: 1; }
			.fh-tooltip::after {
				content: "";
				position: absolute;
				top: 100%;
				left: var(--arrow-x, 50%);
				transform: translateX(-50%);
				border: 5px solid transparent;
				border-top-color: #1e293b;
			}
			.fh-tooltip.is-below::after {
				top: auto;
				bottom: 100%;
				border-top-color: transparent;
				border-bottom-color: #1e293b;
			}

			.fh-empty {
				padding: 1.2rem 0.75rem;
				font-size: 0.8rem;
				color: #94a3b8;
				text-align: center;
			}
			.fh-empty.is-clear { color: #047857; font-weight: var(--weight-semibold); }

			/* ── Assignee avatars ───────────────────────────────── */
			.fh-avatar-col {
				display: flex;
				align-items: center;
				justify-content: flex-end;
				width: 68px;
				flex-shrink: 0;
			}
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
				font-weight: var(--weight-semibold);
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
				font-weight: var(--weight-semibold);
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
			.fh-due-btn--overdue   { color: #ef4444; }
			.fh-due-btn--due_today { color: #f97316; }
			.fh-due-btn--due_soon  { color: #2563eb; }
			.fh-due-btn--stale     { color: #7c3aed; }

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
			.fh-cal__month { font-size: 0.8rem; font-weight: var(--weight-semibold); color: #0f172a; }
			.fh-cal__grid {
				display: grid;
				grid-template-columns: repeat(7, 1fr);
				gap: 1px;
			}
			.fh-cal__dow {
				text-align: center;
				font-size: 0.62rem;
				font-weight: var(--weight-semibold);
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
			.fh-cal__day.is-today { font-weight: var(--weight-bold); color: #2563eb; }
			.fh-cal__day.is-selected { background: #2563eb !important; color: #fff !important; font-weight: var(--weight-semibold); }

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
				font-weight: var(--weight-medium);
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
				font-weight: var(--weight-medium);
				color: #94a3b8;
				transition: background 100ms;
			}
			.fh-due-pop__clear:hover { background: #fff1f2; color: #ef4444; }

			/* ── Add assignee button ──────────────────────────── */
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

			/* Add assignee popover */
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
			.fh-avatars.fh-add-alloc {
				cursor: pointer;
				width: auto;
				height: auto;
				border-radius: 0;
				background: none;
				border: none;
			}

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
				font-weight: var(--weight-semibold);
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
			.fh-health-divider {
				border: none;
				border-top: 1px solid var(--border-color);
				margin: 0.5rem 0.6rem 0;
			}
			.fh-health-section-title {
				font-size: 0.7rem;
				font-weight: var(--weight-semibold);
				color: var(--text-muted);
				text-transform: uppercase;
				letter-spacing: 0.04em;
				padding: 0.45rem 0.6rem 0.1rem;
			}

			/* ── Throughput ─────────────────────────────────────── */
			.fh-throughput { padding: 0 0.6rem 0.65rem; }
			.fh-sparkline-wrap {
				margin-bottom: 0.6rem;
			}
			.fh-sparkline {
				display: block;
				width: 100%;
				height: 40px;
				overflow: visible;
			}
			.fh-sparkline__day-labels {
				display: flex;
				justify-content: space-between;
				margin-top: 0.15rem;
			}
			.fh-sparkline__day-labels span {
				font-size: 0.65rem;
				color: var(--text-muted);
				text-align: center;
				flex: 1;
			}
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
				font-weight: var(--weight-semibold);
				color: #0f172a;
				flex-shrink: 0;
			}
			.fh-net {
				margin-top: 0.45rem;
				padding: 0.32rem 0.5rem;
				border-radius: 7px;
				font-size: 0.76rem;
				font-weight: var(--weight-semibold);
				display: flex;
				align-items: center;
				justify-content: space-between;
				gap: 0.5rem;
			}
			.fh-net__main { flex: 1; text-align: center; }
			.fh-net__prev { font-size: 0.7rem; font-weight: var(--weight-medium); opacity: 0.8; white-space: nowrap; }
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
	}

	_init_tooltip() {
		if (document.getElementById("fh-tooltip")) return;
		const el = document.createElement("div");
		el.id = "fh-tooltip";
		el.className = "fh-tooltip";
		document.body.appendChild(el);

		let current = null;

		const show = (target, tip) => {
			el.textContent = tip;
			el.style.top = "-9999px";
			el.style.left = "0";
			el.classList.add("is-visible");
			requestAnimationFrame(() => {
				const r = target.getBoundingClientRect();
				const w = el.offsetWidth;
				const h = el.offsetHeight;
				const elementCenterX = r.left + r.width / 2;
				let top = r.top - h - 8;
				let left = elementCenterX - w / 2;
				left = Math.max(4, Math.min(left, window.innerWidth - w - 4));
				const isBelow = top < 4;
				if (isBelow) top = r.bottom + 8;
				el.classList.toggle("is-below", isBelow);
				el.style.setProperty("--arrow-x", (elementCenterX - left) + "px");
				el.style.top = top + "px";
				el.style.left = left + "px";
			});
		};

		const hide = () => {
			el.classList.remove("is-visible");
			current = null;
		};

		document.addEventListener("mouseover", (e) => {
			const target = e.target.closest("[data-tip]");
			if (target === current) return;
			current = target || null;
			if (!target) { hide(); return; }
			const tip = target.getAttribute("data-tip");
			if (!tip) { hide(); return; }
			show(target, tip);
		});

		document.addEventListener("mouseleave", hide, true);
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
		if (tab === "health") {
			body = this._render_health(s.throughput_7d || {}, s.risk || []);
		} else {
			const { queue, title } = this._queue_for_tab(s, tab);
			const queueHtml = this._render_focus_queue(queue, title);
			const queuePanel = `<div class="fh-panel fh-panel--queue"><div class="fh-panel__head"><h2 class="fh-panel__title">${this.esc(title)}</h2></div>${queueHtml}</div>`;
			body = this._selected_todo
				? `<div class="fh-queue-layout">${queuePanel}${this._render_detail(this._selected_todo)}</div>`
				: queuePanel;
		}
		this.$root.html(`
			${this._render_status_bar(s.attention || "", s.updated_at, s.counts || [], s.throughput_7d || {})}
			${body}
		`);
		this._bind_events(s);
		if (this._selected_todo) {
			requestAnimationFrame(() => this._apply_queue_layout_stretch());
		}
	}

	_apply_queue_layout_stretch() {
		const $layout = this.$root.find(".fh-queue-layout");
		if (!$layout.length) return;
		const layout = $layout[0];

		layout.style.width = "";
		layout.style.marginLeft = "";
		layout.style.marginRight = "";

		const rect = layout.getBoundingClientRect();
		const viewportWidth = document.documentElement.clientWidth || window.innerWidth;
		const rightInset = 1;
		const targetRight = viewportWidth - rightInset;
		const extraLeft = Math.max(0, rect.left);
		const extraRight = Math.max(0, targetRight - rect.right);
		const overflowRight = Math.max(0, rect.right - targetRight);
		const totalExtra = extraLeft + extraRight;
		const shiftLeft = extraLeft + overflowRight;
		if (totalExtra <= 0 && shiftLeft <= 0) return;

		layout.style.width = `calc(100% + ${totalExtra}px)`;
		layout.style.marginLeft = `${-shiftLeft}px`;
		layout.style.marginRight = `${-extraRight}px`;
	}

	_queue_for_tab(s, tab) {
		const q = s.focus_queue || [];
		switch (tab) {
			case "overdue":      return { queue: q.filter(r => r.urgency_band === "overdue"), title: __("Overdue") };
			case "due_today":    return { queue: q.filter(r => r.urgency_band === "due_today"), title: __("Due Today") };
			case "due_soon":     return { queue: q.filter(r => r.urgency_band === "due_soon"), title: __("Due Soon") };
			case "in_progress":  return { queue: q.filter(r => r.status === "In Progress"), title: __("In Progress") };
			case "action_queue": return { queue: q, title: __("Action Queue") };
			default: {
				const focus = q.filter(r =>
					r.urgency_band === "overdue" ||
					r.urgency_band === "due_today" ||
					r.status === "In Progress"
				);
				return { queue: focus, title: __("Focus") };
			}
		}
	}

	// ── Section renderers ────────────────────────────────────────────

	_chip_icon(key, accented) {
		const MAP = {
			overdue:      "es-line-overdue",
			due_today:    "es-line-today",
			due_soon:     "es-line-tomorrow",
			in_progress:  "es-solid-inprogress",
			health:       "es-line-activity",
			action_queue: "es-line-bullet-list",
		};
		const id = MAP[key];
		if (!id) return "";
		const base = id.startsWith("es-solid") ? "es-icon es-solid" : "es-icon es-line";
		const accent = accented ? " is-accented" : "";
		return `<svg class="fh-chip__icon ${base}${accent}"><use href="#${id}"></use></svg>`;
	}

	_render_health_chip(t) {
		const net = t.net !== undefined ? t.net : 0;
		const trend = t.trend || "stable";
		const isActive = this._active_tab === "health";

		let accent;
		if (net > 0)       accent = "#059669";
		else if (net < 0)  accent = "#e11d48";
		else               accent = "#64748b";

		const trendLabel = trend === "improving" ? "↑ improving" : trend === "worsening" ? "↓ worsening" : "→ stable";
		const sign = net > 0 ? "+" : "";
		const tip = `${__("Velocity")}: ${sign}${net} · ${trendLabel}`;

		return `<button type="button" class="fh-chip ${isActive ? "is-active" : ""}"
			data-chip-key="health"
			data-tip="${this.esc(tip)}"
			style="--fh-accent:${accent}">
			${this._chip_icon("health", true)}
			<span class="fh-chip__value ${net !== 0 ? "is-nonzero" : ""}">${sign}${net}</span>
		</button>`;
	}

	_render_status_bar(attention, updatedAt, counts, throughput) {
		const msgClass = attention.startsWith("Welcome") ? "is-clear" : "is-ahead";

		// Auto-prune: hide zero-count chips unless they are the active tab
		const visibleCounts = (counts || []).filter(c => c.value > 0 || this._active_tab === c.key);

		const countChips = visibleCounts.map(c => {
			const isActive = this._active_tab === c.key;
			const isNonZero = c.value > 0;
			return `<button type="button" class="fh-chip ${isActive ? "is-active" : ""}"
				data-chip-key="${this.esc(c.key)}"
				${c.label ? `data-tip="${this.esc(c.label)}"` : ""}
				style="--fh-accent:${this.esc(c.accent || "var(--primary)")}">
				${this._chip_icon(c.key, isNonZero)}
				<span class="fh-chip__value ${isNonZero ? "is-nonzero" : ""}">${c.value}</span>
			</button>`;
		}).join("");

		const isActionActive = this._active_tab === "action_queue";
		return `
			<div class="fh-status">
				<span class="fh-status__msg ${msgClass}">${this.esc(attention)}</span>
				<div class="fh-chips">
					${countChips}
					${this._render_health_chip(throughput)}
					<button type="button" class="fh-chip ${isActionActive ? "is-active" : ""}"
						data-chip-key="action_queue" data-tip="${this.esc(__("Action Queue"))}" style="--fh-accent:#0ea5e9">
						${this._chip_icon("action_queue", isActionActive)}
					</button>
				</div>
				<span class="fh-status__time">${this._fmt_time(updatedAt)}</span>
			</div>
		`;
	}

	_render_focus_queue(queue, title) {
		const body = queue.length
			? queue
					.map((row, i) => {
						const band = row.urgency_band || "active";
						const dueTooltip = row.due_date
							? new Date(row.due_date + "T00:00:00").toLocaleDateString(undefined, {
								weekday: "short", month: "short", day: "numeric",
							  })
							: "";
						const dueBandClass = band !== "active" ? `fh-due-btn--${band}` : "";
						const dueLabel = row.due_label
							? `<span role="button" class="fh-due-btn ${dueBandClass}" data-due-todo="${this.esc(row.name)}" data-due-date="${this.esc(row.due_date || '')}"${dueTooltip ? ` data-tip="${this.esc(dueTooltip)}"` : ""}>${this.esc(row.due_label)}</span>`
							: `<span role="button" class="fh-due-btn fh-due-btn--empty" data-due-todo="${this.esc(row.name)}" data-due-date="" title="${this.esc(__('Set due date'))}">📅</span>`;
						const avatars = this._render_avatars(row.assignees, row.name);
						const pc = this._prio_config(row.priority);
						const prioTip = this.esc(row.priority || __("Priority"));
						const isSelected = this._selected_todo?.name === row.name;
						return `
						<button type="button" class="fh-item fh-band-${band}${isSelected ? " is-selected" : ""}" data-queue-index="${i}">
							<span role="button" class="fh-prio-btn" data-tip="${prioTip}" data-prio-index="${i}" data-todo-name="${this.esc(row.name)}" style="color:${pc.color}">${pc.icon}</span>
							<div class="fh-item__body">
								<div class="fh-item__title">${this.esc(row.title || row.name || "")}</div>
							</div>
							<div class="fh-item__due">${dueLabel}</div>
							${avatars}
						</button>
					`;
					})
					.join("")
			: `<div class="fh-empty is-clear">${this.esc(
					__("All clear.")
			  )}</div>`;

		return `<div class="fh-queue">${body}</div>`;
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

	_render_health(throughput, risk) {
		const created = throughput.created || 0;
		const closed = throughput.closed || 0;
		const net = throughput.net !== undefined ? throughput.net : closed - created;
		const prevNet = throughput.prev_net !== undefined ? throughput.prev_net : null;
		const trend = throughput.trend || "stable";
		const maxVal = Math.max(created, closed, 1);
		const createdPct = Math.round((created / maxVal) * 100);
		const closedPct = Math.round((closed / maxVal) * 100);

		let netClass;
		if (net > 0)       netClass = "is-ahead";
		else if (net < 0)  netClass = "is-behind";
		else               netClass = "is-neutral";

		const sign = net > 0 ? "+" : "";
		const netLabel = net === 0 ? __("Balanced") : __("Net {0}", [sign + net]);

		let prevText = "";
		if (prevNet !== null) {
			const prevSign = prevNet > 0 ? "+" : "";
			const trendIcon = trend === "improving" ? "↑" : trend === "worsening" ? "↓" : "→";
			prevText = `<span class="fh-net__prev">${trendIcon} ${__("prev")} ${prevSign}${prevNet}</span>`;
		}

		const riskRows = (risk || [])
			.map((r, i) => `
				<div class="fh-risk-row" data-risk-index="${i}" role="button">
					<span class="fh-risk-row__label">${this.esc(r.label || "")}</span>
					<span class="fh-risk-row__value ${r.value === 0 ? "is-zero" : ""}">${r.value}</span>
					<span class="fh-risk-row__arrow">›</span>
				</div>
			`)
			.join('<hr class="fh-divider">');

		return `
			<div class="fh-panel">
				<div class="fh-panel__head">
					<h2 class="fh-panel__title">${this.esc(__("Health"))}</h2>
				</div>
				<div class="fh-health-section-title">${this.esc(__("Velocity"))}</div>
				<div class="fh-throughput">
					${this._render_sparkline(throughput.daily_closed)}
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
					<div class="fh-net ${netClass}">
						<span class="fh-net__main">${this.esc(netLabel)}</span>
						${prevText}
					</div>
				</div>
				<hr class="fh-health-divider">
				<div class="fh-health-section-title">${this.esc(__("Risk Signals"))}</div>
				<div class="fh-risk">${riskRows}</div>
			</div>
		`;
	}

	_render_sparkline(dailyClosed) {
		const days = dailyClosed || Array(7).fill(0);
		const maxVal = Math.max(...days, 1);
		const W = 200;
		const H = 40;
		const barW = Math.floor(W / days.length);
		const gap = 3;
		const innerW = barW - gap;

		const bars = days.map((v, i) => {
			const h = Math.max(Math.round((v / maxVal) * H), v > 0 ? 3 : 1);
			const x = i * barW + Math.floor(gap / 2);
			const y = H - h;
			const opacity = v > 0 ? 1 : 0.18;
			return `<rect x="${x}" y="${y}" width="${innerW}" height="${h}" rx="2" fill="#059669" opacity="${opacity}"/>`;
		}).join("");

		const today = new Date();
		const labels = days.map((_, i) => {
			const d = new Date(today);
			d.setDate(d.getDate() - (6 - i));
			return `<span>${d.toLocaleDateString(undefined, { weekday: "narrow" })}</span>`;
		}).join("");

		return `
			<div class="fh-sparkline-wrap">
				<svg class="fh-sparkline" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${bars}</svg>
				<div class="fh-sparkline__day-labels">${labels}</div>
			</div>
		`;
	}

	_render_throughput(t) {
		const created = t.created || 0;
		const closed = t.closed || 0;
		const net = t.net !== undefined ? t.net : closed - created;
		const prevNet = t.prev_net !== undefined ? t.prev_net : null;
		const trend = t.trend || "stable";
		const maxVal = Math.max(created, closed, 1);
		const createdPct = Math.round((created / maxVal) * 100);
		const closedPct = Math.round((closed / maxVal) * 100);

		let netClass;
		if (net > 0)       netClass = "is-ahead";
		else if (net < 0)  netClass = "is-behind";
		else               netClass = "is-neutral";

		const sign = net > 0 ? "+" : "";
		const netLabel = net === 0 ? __("Balanced") : __("Net {0}", [sign + net]);

		let prevText = "";
		if (prevNet !== null) {
			const prevSign = prevNet > 0 ? "+" : "";
			const trendIcon = trend === "improving" ? "↑" : trend === "worsening" ? "↓" : "→";
			prevText = `<span class="fh-net__prev">${trendIcon} ${__("prev")} ${prevSign}${prevNet}</span>`;
		}

		return `
			<div class="fh-panel">
				<div class="fh-panel__head">
					<h2 class="fh-panel__title">${this.esc(__("Velocity"))}</h2>
				</div>
				<div class="fh-throughput">
					${this._render_sparkline(t.daily_closed)}
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
					<div class="fh-net ${netClass}">
						<span class="fh-net__main">${this.esc(netLabel)}</span>
						${prevText}
					</div>
				</div>
			</div>
		`;
	}

	// ── Event binding ─────────────────────────────────────────────────

	_bind_events(s) {
		const counts = s.counts || [];
		const queue = s.focus_queue || [];
		const risk = s.risk || [];

		this.$root.find("[data-chip-key]").on("click", (e) => {
			const key = $(e.currentTarget).attr("data-chip-key");
			this._active_tab = (this._active_tab === key) ? null : key;
			this._selected_todo = null;
			this.render();
		});

		this.$root.find("[data-queue-index]").each((_, el) => {
			const row = queue[parseInt($(el).attr("data-queue-index"), 10)];
			if (row?.name) $(el).on("click", () => {
				this._selected_todo = (this._selected_todo?.name === row.name) ? null : row;
				this.render();
			});
		});

		this.$root.find("[data-close-detail]").on("click", () => {
			this._selected_todo = null;
			this.render();
		});

		this.$root.find("[data-prio-index]").on("click", (e) => {
			e.stopPropagation();
			this._open_prio_dropdown(e.currentTarget);
		});

		this.$root.find("[data-add-alloc]").on("click", (e) => {
			e.stopPropagation();
			this._open_assignee_popover(e.currentTarget);
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
			return `<span class="fh-avatar-col">
				<span role="button" tabindex="0" class="fh-add-alloc" data-tip="${this.esc(__("Add Assignee"))}" ${nameAttr}>
					<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
						<path d="M12 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10zm0 2c-5.33 0-8 2.67-8 4v1h16v-1c0-1.33-2.67-4-8-4z"/>
					</svg>
				</span>
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
		return `<span class="fh-avatar-col">
			<span role="button" tabindex="0" class="fh-avatars fh-add-alloc" ${nameAttr}>${chips}${more}</span>
		</span>`;
	}

	_open_assignee_popover(btn) {
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
				this._search_assignee_users($(e.target).val(), $pop, existing);
			});

			$pop.on("click", ".fh-alloc-pop__opt[data-user]", (e) => {
				e.stopPropagation();
				const user = $(e.currentTarget).attr("data-user");
				const name = $($pop.data("active-btn")).attr("data-add-alloc");
				if (!user || !name) return;
				$pop.removeClass("is-open");
				frappe.call({
					method: "opero.todo_dashboard.add_todo_assignee",
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
					method: "opero.todo_dashboard.remove_todo_assignee",
					args: { todo_name: name, user },
					callback: () => this.refresh({ force: true }),
				});
			});
		}

		if ($pop.hasClass("is-open") && $pop.data("active-btn") === btn) {
			$pop.removeClass("is-open");
			return;
		}

		// Render current assignees with remove buttons
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
		this._search_assignee_users("", $pop, existing);

		setTimeout(() => {
			$(document).one("click.fh-alloc", () => $pop.removeClass("is-open"));
		}, 0);
	}

	_search_assignee_users(query, $pop, excludeSet = new Set()) {
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
		const ALL_DOWS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
		const weekStartName = frappe.sys_defaults?.first_day_of_the_week || "Sunday";
		const weekStart = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"].indexOf(weekStartName);
		const startDay = weekStart < 0 ? 0 : weekStart;
		const DOWS = [...ALL_DOWS.slice(startDay), ...ALL_DOWS.slice(0, startDay)];

		const today = frappe.datetime.get_today();
		const rawFirstDay = new Date(year, month, 1).getDay();
		const firstDay = (rawFirstDay - startDay + 7) % 7;
		const daysInMonth = new Date(year, month + 1, 0).getDate();
		const daysInPrev  = new Date(year, month, 0).getDate();
		const monthLabel  = new Date(year, month, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" });

		let cells = "";
		for (let i = firstDay - 1; i >= 0; i--) {
			cells += `<span class="fh-cal__day is-other">${daysInPrev - i}</span>`;
		}
		for (let d = 1; d <= daysInMonth; d++) {
			const ds = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
			let cls = "fh-cal__day";
			if (ds === today) cls += " is-today";
			if (ds === selectedDate) cls += " is-selected";
			cells += `<span class="${cls}" data-cal-date="${ds}">${d}</span>`;
		}
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
			args: { doctype: "ToDo", name: todoName, fieldname: "date", value: date || null },
			callback: () => this.refresh({ force: true }),
		});
	}

	_render_detail(todo) {
		const name      = todo.name || "";
		const title     = todo.title || todo.name || "";
		const status    = todo.status || "";
		const priority  = todo.priority || "";
		const dueLabel  = todo.due_label || "";
		const band      = todo.urgency_band || "";
		const dueBandClass = band && band !== "active" ? `fh-due-btn--${band}` : "";
		const desc      = (todo.description || "").trim();
		const assignees = todo.assignees || [];

		const priorityPc = this._prio_config(priority);
		const assigneeList = assignees.length
			? assignees.map(a => `<span class="fh-detail__assignee">
					<span class="fh-avatar" style="width:18px;height:18px;font-size:0.55rem;background:${this._avatar_color(a.user)}">${this.esc(a.initials)}</span>
					${this.esc(a.full_name || a.user)}
				</span>`).join("")
			: `<span style="color:#94a3b8">${__("Unassigned")}</span>`;

		const rows = [
			{ key: __("Status"),   val: `<span style="color:#334155">${this.esc(status)}</span>` },
			priority ? { key: __("Priority"), val: `<span style="color:${priorityPc.color}">${priorityPc.icon} ${this.esc(priority)}</span>` } : null,
			dueLabel ? { key: __("Due"),      val: `<span class="fh-due-btn ${dueBandClass}" style="cursor:default">${this.esc(dueLabel)}</span>` } : null,
			{ key: __("Assigned"), val: `<span class="fh-detail__assignees">${assigneeList}</span>` },
		].filter(Boolean);

		return `<div class="fh-detail">
			<div class="fh-detail__bar">
				<button type="button" class="fh-detail__close" data-close-detail title="${__("Close")}">✕</button>
				<a class="fh-detail__open" href="/app/todo/${this.esc(name)}">${__("Open in form")} ↗</a>
			</div>
			<div class="fh-detail__scroll">
				<h3 class="fh-detail__title">${this.esc(title)}</h3>
				<div class="fh-detail__fields">
					${rows.map(r => `<div class="fh-detail__row">
						<span class="fh-detail__key">${r.key}</span>
						<span class="fh-detail__val">${r.val}</span>
					</div>`).join("")}
				</div>
				${desc ? `<div class="fh-detail__desc">${desc}</div>` : ""}
			</div>
		</div>`;
	}

	_avatar_color(user) {
		const PALETTE = ["#2563eb","#059669","#d97706","#7c3aed","#db2777","#0891b2","#65a30d","#dc2626"];
		let h = 0;
		for (let i = 0; i < (user||"").length; i++) h = (h * 31 + user.charCodeAt(i)) >>> 0;
		return PALETTE[h % PALETTE.length];
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
