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
		this._saving = 0;
		this._detail_context = {};
		this._detail_loading = new Set();
		this._description_draft = null;
		this._queue_layout_open_raf = null;
		this._queue_layout_resize_raf = null;
		this._on_window_resize = () => {
			if (!this._selected_todo) return;
			if (this._queue_layout_resize_raf) cancelAnimationFrame(this._queue_layout_resize_raf);
			this._queue_layout_resize_raf = requestAnimationFrame(() => {
				this._queue_layout_resize_raf = null;
				this._apply_queue_layout_open_state();
			});
		};
		window.addEventListener("resize", this._on_window_resize);
		document.addEventListener("keydown", (e) => {
			if (e.key !== "Escape") return;
			$("#fh-prio-drop, #fh-due-pop, #fh-alloc-pop").removeClass("is-open");
		});

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
		this._setup_realtime_sync();
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
				.fh,
				.fh * {
					font-family: var(--font-stack);
					font-weight: var(--weight-regular) !important;
				}

				/* ── Status bar ─────────────────────────────────────── */
				.fh-status {
				display: flex;
				align-items: stretch;
				height: 46px;
				border-radius: 10px;
				background: var(--bg-color);
				border: 1px solid var(--border-color);
				margin-bottom: 0.65rem;
				padding: 0 0.3rem;
				gap: 0;
			}
			.fh-status__msg {
				flex-shrink: 0;
				display: flex;
				align-items: center;
				padding: 0 0.75rem;
				font-size: var(--text-sm);
				font-weight: var(--weight-semibold);
				color: #64748b;
				white-space: nowrap;
			}
			.fh-status__msg.is-ahead { color: #047857; }
			.fh-status__sep {
				width: 1px;
				align-self: center;
				height: 18px;
				background: var(--border-color);
				flex-shrink: 0;
				margin: 0 0.1rem;
			}
			.fh-status__time {
				flex-shrink: 0;
				display: flex;
				align-items: center;
				padding: 0 0.75rem;
				font-size: var(--text-tiny);
				color: var(--text-muted);
				white-space: nowrap;
				margin-left: auto;
			}
			.fh-status__time .frappe-timestamp { pointer-events: none; }

			/* ── Chips ───────────────────────────────────────────── */
			.fh-chips {
				display: flex;
				align-items: stretch;
				gap: 0;
				flex: 1;
				min-width: 0;
				padding: 0 0.3rem;
			}
			.fh-chip {
				display: flex;
				align-items: center;
				gap: 0.22rem;
				padding: 0 0.55rem;
				border: none;
				border-bottom: 2px solid transparent;
				background: transparent;
				border-radius: 0;
				cursor: pointer;
				transition: border-color 120ms, color 120ms;
				white-space: nowrap;
				flex-shrink: 0;
			}
			.fh-chip:hover { background: rgba(0,0,0,0.04); }
			.fh-chip.is-active {
				border-bottom-color: var(--fh-accent, var(--primary));
			}
.fh-chip__label {
				font-size: var(--text-xs);
				font-weight: var(--weight-medium);
				color: var(--text-muted);
				transition: color 120ms;
			}
			.fh-chip.is-active .fh-chip__label {
				font-weight: var(--weight-semibold);
				color: var(--text-color);
			}
			.fh-chip__value {
				font-size: var(--text-xs);
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
				font-size: var(--text-tiny);
				font-weight: var(--weight-semibold);
				color: var(--text-muted);
				text-transform: uppercase;
				letter-spacing: 0.07em;
				margin: 0;
			}
			.fh-panel__sub {
				font-size: var(--text-xs);
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
				padding: 0.3rem 0.75rem;
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
				font-size: var(--text-base);
				font-weight: var(--weight-regular);
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
				font-size: var(--text-xs);
				color: var(--text-muted);
			}

			/* ── Queue + detail split ───────────────────────────── */
			.fh-queue-layout {
				display: grid;
				grid-template-columns: minmax(0, 1fr) clamp(360px, 36vw, 480px);
				gap: 0;
				width: 100%;
				min-width: 0;
				align-items: stretch;
				overflow: visible;
			}
			.fh-queue-layout > .fh-panel--queue {
				min-width: 0;
				border-right: none;
				border-radius: 10px 0 0 10px;
				overflow-y: auto;
				overflow-x: hidden;
			}

			/* ── Detail panel ───────────────────────────────────── */
			.fh-detail {
				display: flex;
				flex-direction: column;
				min-width: 0;
				min-height: 0;
				background: var(--fg-color);
				border: 1px solid var(--border-color);
				border-left: none;
				border-radius: 0 10px 10px 0;
				transform: translateX(18px);
				opacity: 0;
				pointer-events: none;
				transition: transform 280ms ease-in-out, opacity 190ms ease-in-out;
			}
			.fh-detail__scrim {
				display: none;
			}
			.fh-queue-layout.is-detail-open .fh-detail {
				transform: translateX(0);
				opacity: 1;
				pointer-events: auto;
			}
			.fh-detail__actions {
				flex: 0 0 auto;
				display: flex;
				align-items: center;
				gap: 0.22rem;
				padding: 0.45rem 0.55rem;
				border-bottom: 1px solid var(--border-color);
				background: var(--fg-color);
			}
			.fh-detail__action-btn {
				display: inline-flex;
				align-items: center;
				gap: 0.24rem;
				border: 1px solid var(--border-color);
				border-radius: 6px;
				background: var(--fg-color);
				color: var(--text-color);
				font-size: var(--text-xs);
				padding: 0.24rem 0.42rem;
				cursor: pointer;
				transition: background 120ms ease;
			}
			.fh-detail__action-btn:hover { background: var(--bg-color); }
			.fh-detail__action-btn.is-quiet {
				border: none;
				padding: 0.24rem 0.3rem;
				color: var(--text-muted);
			}
			.fh-detail__action-btn.is-quiet:hover { color: var(--text-color); }
			.fh-detail__action-btn.is-link {
				border: none;
				color: var(--primary);
				padding: 0.24rem 0.3rem;
				text-decoration: none;
			}
			.fh-detail__action-btn.is-link:hover { background: var(--bg-color); text-decoration: none; }
			.fh-detail__action-btn.is-primary {
				border-color: #bbf7d0;
				background: #f0fdf4;
				color: #15803d;
			}
			.fh-detail__action-btn.is-primary:hover {
				background: #dcfce7;
			}
			.fh-detail__action-spacer {
				flex: 1;
				min-width: 0;
			}
			.fh-detail__content {
				flex: 1 1 auto;
				min-height: 0;
				overflow: auto;
				padding: 0.8rem 0.85rem 0.9rem;
			}
			.fh-detail__title-wrap {
				display: flex;
				align-items: flex-start;
				gap: 0.55rem;
				margin-bottom: 0.7rem;
			}
			.fh-detail__checkbox {
				width: 24px;
				height: 24px;
				border-radius: 50%;
				border: 2px solid #cbd5e1;
				background: transparent;
				flex-shrink: 0;
				line-height: 1;
				cursor: pointer;
				color: #cbd5e1;
			}
			.fh-detail__checkbox:hover { border-color: #94a3b8; color: #94a3b8; }
			.fh-detail__title {
				font-size: var(--text-3xl, 2rem);
				line-height: 1.22;
				margin: 0;
				color: var(--text-color);
			}
			.fh-detail__meta {
				display: flex;
				align-items: center;
				flex-wrap: wrap;
				gap: 0.45rem 0.62rem;
				margin-bottom: 0.72rem;
			}
			.fh-detail__meta-chip {
				display: inline-flex;
				align-items: center;
				font-size: var(--text-xs);
				color: var(--text-color);
				gap: 0.3rem;
			}
			.fh-detail__meta-chip.is-quiet { color: var(--text-muted); }
			.fh-detail__meta-chip.is-due {
				border: none;
				background: transparent;
				padding: 0;
			}
			.fh-detail__meta-chip.is-assignee {
				border: none;
				background: transparent;
				padding: 0;
				cursor: pointer;
			}
			.fh-detail__meta-chip.is-assignee:hover {
				color: var(--primary);
			}
			.fh-detail__meta-text {
				display: inline-flex;
				align-items: center;
				gap: 0.18rem;
				min-width: 0;
			}
			.fh-detail__divider {
				border: none;
				border-top: 1px solid var(--border-color);
				margin: 0.35rem 0 0;
			}
			.fh-detail__section {
				padding: 0.2rem 0;
				border-bottom: 1px solid var(--border-color);
			}
			.fh-detail__section:last-child {
				border-bottom: none;
			}
			.fh-detail__line {
				display: flex;
				align-items: center;
				gap: 0.5rem;
				width: 100%;
				border: none;
				background: transparent;
				padding: 0.46rem 0;
				font-size: var(--text-lg);
				color: var(--text-color);
				text-align: left;
				cursor: pointer;
			}
			.fh-detail__line:hover { color: var(--primary); }
			.fh-detail__line.is-static {
				cursor: default;
				color: var(--text-muted);
			}
			.fh-detail__line.is-static:hover { color: var(--text-muted); }
			.fh-detail__line-icon {
				font-size: var(--text-xl);
				width: 22px;
				text-align: center;
				flex-shrink: 0;
				color: var(--text-muted);
			}
			.fh-detail__line-content {
				flex: 1;
				min-width: 0;
			}
			.fh-detail__line-tail {
				display: inline-flex;
				align-items: center;
				gap: 0.3rem;
				flex-shrink: 0;
			}
			.fh-detail__line-title {
				font-size: var(--text-lg);
				color: var(--text-color);
				line-height: 1.4;
			}
			.fh-detail__line-sub {
				font-size: var(--text-sm);
				color: var(--text-muted);
				margin-top: 0.08rem;
				line-height: 1.35;
			}
			.fh-detail__line-tags {
				display: flex;
				align-items: center;
				flex-wrap: wrap;
				gap: 0.25rem;
				margin-top: 0.25rem;
			}
			.fh-detail__tag {
				display: inline-flex;
				align-items: center;
				gap: 0.2rem;
				border: 1px solid var(--border-color);
				border-radius: 999px;
				padding: 0.14rem 0.44rem;
				font-size: var(--text-tiny);
				color: var(--text-color);
				background: var(--fg-color);
			}
			.fh-detail__tag-remove {
				border: none;
				background: transparent;
				padding: 0;
				color: var(--text-muted);
				cursor: pointer;
				line-height: 1;
			}
			.fh-detail__tag-remove:hover { color: #dc2626; }

			/* ── Members section ─────────────────────────────────── */
			.fh-members__grid {
				display: grid;
				grid-template-columns: 1fr 1fr;
				gap: 0 0.5rem;
			}
			.fh-member-chip {
				display: inline-flex;
				align-items: center;
				gap: 0.22rem;
				border: 1px solid var(--border-color);
				border-radius: 999px;
				padding: 0.2rem 0.45rem 0.2rem 0.3rem;
				font-size: var(--text-sm);
				color: var(--text-color);
				background: var(--bg-color);
			}
			.fh-member-chip.is-main {
				border-color: var(--border-color);
				background: var(--bg-color);
			}
			.fh-member-chip__promote {
				border: none;
				background: transparent;
				padding: 0;
				cursor: pointer;
				font-size: 0.7rem;
				line-height: 1;
				color: var(--border-color);
				flex-shrink: 0;
			}
			.fh-member-chip.is-main .fh-member-chip__promote {
				color: var(--primary);
				cursor: default;
			}
			.fh-member-chip__promote:hover { color: var(--primary); }
			.fh-member-chip.is-main .fh-member-chip__promote:hover { color: var(--primary); }
			.fh-member-chip__name { line-height: 1.3; }
			.fh-member-chip__remove {
				border: none;
				background: transparent;
				padding: 0 0.05rem;
				cursor: pointer;
				color: transparent;
				font-size: var(--text-sm);
				line-height: 1;
				flex-shrink: 0;
				transition: color 120ms;
			}
			.fh-member-chip:hover .fh-member-chip__remove { color: var(--text-color); }
			.fh-member-chip__remove:hover { color: #dc2626; }
			.fh-members__chips {
				display: flex;
				flex-wrap: wrap;
				align-items: center;
				gap: 0.3rem;
				min-height: 1.4rem;
			}
			.fh-members__add-btn {
				border: 1px dashed var(--border-color);
				border-radius: 999px;
				background: transparent;
				padding: 0.2rem 0.55rem;
				font-size: var(--text-sm);
				color: var(--text-muted);
				cursor: pointer;
				white-space: nowrap;
			}
			.fh-members__add-btn:hover { border-color: var(--primary); color: var(--primary); }

			/* ── Outlined field (legend-on-border pattern) ───────── */
			.fh-field-outlined {
				position: relative;
				border: 1px solid var(--border-color);
				border-radius: 6px;
				padding: 0.55rem 0.75rem 0.5rem;
				margin: 0.55rem 0;
			}
			.fh-field-outlined__label {
				position: absolute;
				top: -0.55em;
				left: 0.6rem;
				padding: 0 0.25rem;
				background: var(--fg-color);
				font-size: var(--text-xs);
				font-weight: var(--weight-medium);
				color: var(--text-muted);
				line-height: 1;
				letter-spacing: 0.01em;
				pointer-events: none;
			}
			.fh-field-outlined__body {
				display: flex;
				align-items: center;
				justify-content: space-between;
				gap: 0.5rem;
			}
			.fh-field-outlined__value {
				font-size: var(--text-base);
				color: var(--text-color);
				flex: 1;
				min-width: 0;
			}
			.fh-field-outlined__value.is-empty { color: var(--text-muted); }
			.fh-field-outlined__actions {
				display: inline-flex;
				align-items: center;
				gap: 0.3rem;
				flex-shrink: 0;
			}
			.fh-field-outlined--clickable {
				cursor: text;
				transition: border-color 120ms;
			}
			.fh-field-outlined--clickable:hover { border-color: var(--primary); }
			.fh-field-outlined--clickable.is-open { border-color: var(--primary); }
			.fh-field-outlined__clear {
				border: none;
				background: transparent;
				color: var(--text-muted);
				cursor: pointer;
				padding: 0 0.1rem;
				font-size: var(--text-base);
				line-height: 1;
				flex-shrink: 0;
			}
			.fh-field-outlined__clear:hover { color: #dc2626; }

			/* ── Project combobox ────────────────────────────────── */
			.fh-project-input {
				flex: 1;
				min-width: 0;
				border: none;
				outline: none;
				background: transparent;
				font-size: var(--text-sm);
				color: var(--text-color);
				padding: 0;
			}
			.fh-project-dropdown {
				position: fixed;
				z-index: 2000;
				background: var(--fg-color);
				border: 1px solid var(--border-color);
				border-radius: 6px;
				box-shadow: 0 4px 16px rgba(0,0,0,0.10);
				list-style: none;
				margin: 0;
				padding: 0.2rem 0;
				max-height: 220px;
				overflow-y: auto;
			}
			.fh-project-dropdown__item {
				padding: 0.38rem 0.75rem;
				cursor: pointer;
				font-size: var(--text-sm);
				color: var(--text-color);
				list-style: none;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
			}
			.fh-project-dropdown__item:hover,
			.fh-project-dropdown__item.is-focused {
				background: var(--bg-color);
				color: var(--primary);
			}
			.fh-project-dropdown__empty {
				padding: 0.4rem 0.75rem;
				font-size: var(--text-sm);
				color: var(--text-muted);
				list-style: none;
			}

			.fh-detail__desc-text {
				font-size: var(--text-lg);
				line-height: 1.45;
				white-space: pre-wrap;
			}
			.fh-detail__desc-empty {
				color: var(--text-muted);
			}
			.fh-detail__desc-editor {
				padding: 0.12rem 0 0.5rem;
			}
			.fh-detail__textarea {
				width: 100%;
				min-height: 102px;
				border: 1px solid var(--border-color);
				border-radius: 8px;
				background: var(--fg-color);
				color: var(--text-color);
				font-size: var(--text-base);
				padding: 0.56rem 0.62rem;
				resize: vertical;
			}
			.fh-detail__editor-actions {
				display: flex;
				gap: 0.34rem;
				margin-top: 0.35rem;
			}
			.fh-detail__btn {
				border: 1px solid var(--border-color);
				border-radius: 7px;
				padding: 0.22rem 0.52rem;
				font-size: var(--text-xs);
				background: var(--fg-color);
				color: var(--text-color);
				cursor: pointer;
			}
			.fh-detail__btn:hover { background: var(--bg-color); }
			.fh-detail__btn.is-primary {
				border-color: #bfdbfe;
				background: #eff6ff;
				color: #1d4ed8;
			}
			.fh-detail__btn.is-primary:hover { background: #dbeafe; }
			.fh-detail__attachment-list {
				display: flex;
				flex-direction: column;
				gap: 0.25rem;
				margin-top: 0.28rem;
			}
			.fh-detail__attachment {
				display: flex;
				align-items: center;
				gap: 0.3rem;
				font-size: var(--text-sm);
				color: var(--text-muted);
			}
			.fh-detail__attachment-link {
				color: var(--text-muted);
				text-decoration: none;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
				max-width: 100%;
			}
			.fh-detail__attachment-link:hover { color: var(--primary); }
			.fh-detail__attachment-remove {
				border: none;
				background: transparent;
				color: var(--text-muted);
				cursor: pointer;
				padding: 0;
				line-height: 1;
			}
			.fh-detail__attachment-remove:hover { color: #dc2626; }
			.fh-detail__section-head {
				display: flex;
				align-items: center;
				justify-content: space-between;
				gap: 0.45rem;
				padding: 0.56rem 0 0.34rem;
			}
			.fh-detail__section-title {
				font-size: var(--text-sm);
				color: var(--text-muted);
			}
			.fh-detail__activity {
				display: flex;
				flex-direction: column;
				gap: 0.48rem;
				padding: 0.1rem 0 0.55rem;
			}
			.fh-detail__activity-item {
				border-left: 2px solid var(--border-color);
				padding-left: 0.5rem;
				min-width: 0;
			}
			.fh-detail__activity-head {
				display: flex;
				align-items: center;
				flex-wrap: wrap;
				gap: 0.28rem;
				font-size: var(--text-xs);
				color: var(--text-muted);
			}
			.fh-detail__activity-type {
				color: var(--text-color);
			}
			.fh-detail__activity-content {
				font-size: var(--text-sm);
				color: var(--text-color);
				line-height: 1.4;
				margin-top: 0.14rem;
				white-space: pre-wrap;
			}
			.fh-detail__activity-empty {
				font-size: var(--text-sm);
				color: var(--text-muted);
				padding: 0.2rem 0 0.55rem;
			}
			.fh-detail__composer {
				flex: 0 0 auto;
				display: flex;
				align-items: center;
				gap: 0.45rem;
				padding: 0.55rem 0.7rem;
				border-top: 1px solid var(--border-color);
				background: var(--fg-color);
			}
			.fh-detail__composer-input {
				flex: 1;
				min-width: 0;
				border: 1px solid var(--border-color);
				border-radius: 7px;
				background: var(--fg-color);
				color: var(--text-color);
				padding: 0.34rem 0.5rem;
				font-size: var(--text-sm);
			}
			.fh-detail__composer-send {
				border: 1px solid var(--border-color);
				border-radius: 7px;
				padding: 0.28rem 0.5rem;
				background: var(--fg-color);
				font-size: var(--text-xs);
				color: var(--text-color);
				cursor: pointer;
			}
			.fh-detail__composer-send:hover { background: var(--bg-color); }
			.fh-detail__loading {
				font-size: var(--text-sm);
				color: var(--text-muted);
				padding: 0.4rem 0;
			}
			.fh-item.is-selected {
				background: var(--bg-color);
				border-left: 3px solid var(--primary);
				border-right: none;
				border-radius: 0;
			}
			.fh-band-overdue:not(.is-selected)   { border-left: 3px solid #fca5a5; }
			.fh-band-due_today:not(.is-selected) { border-left: 3px solid #fdba74; }
			.fh-band-due_soon:not(.is-selected)  { border-left: 3px solid #93c5fd; }
			.fh-band-stale:not(.is-selected)     { border-left: 3px solid #c4b5fd; }

			/* Urgency tag pill — keep hardcoded, these are semantic colours */
			.fh-tag {
				padding: 0.11rem 0.34rem;
				border-radius: 4px;
				font-size: var(--text-tiny);
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
				font-size: var(--text-tiny);
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
				font-size: var(--text-base);
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
				font-size: var(--text-sm);
				font-weight: var(--weight-medium);
				color: #0f172a;
				transition: background 100ms;
			}
			.fh-prio-drop__opt:hover { background: #f8fafc; }
			.fh-prio-drop__opt.is-current { background: #f0fdf4; }
			.fh-prio-drop__check { display: none; margin-left: auto; color: #059669; font-size: var(--text-sm); }
			.fh-prio-drop__opt.is-current .fh-prio-drop__check { display: inline; }
			.fh-prio-drop__icon {
				font-size: var(--text-xs);
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
				font-size: var(--text-xs);
				font-weight: var(--weight-medium);
				padding: 0.3rem 0.6rem;
				border-radius: 5px;
				pointer-events: none;
				white-space: nowrap;
				box-shadow: 0 2px 6px rgba(0,0,0,0.25);
				opacity: 0;
				transition: opacity 0.15s ease;
			}
			.fh-tooltip.is-visible { opacity: 1; }
			.fh-tooltip__name {
				font-size: var(--text-xs);
				font-weight: var(--weight-regular);
				line-height: 1.3;
			}
			.fh-tooltip__roles {
				font-size: var(--text-tiny);
				color: #94a3b8;
				margin-top: 0.18rem;
			}
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
				font-size: var(--text-sm);
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
				font-size: var(--text-tiny);
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
				font-size: var(--text-tiny);
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
				font-size: var(--text-tiny);
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
				background: var(--fg-color);
				border: 1px solid var(--border-color);
				border-radius: 8px;
				box-shadow: var(--shadow-sm, 0 4px 16px rgba(0,0,0,0.12));
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
				font-size: var(--text-lg);
				line-height: 1;
				padding: 0.15rem 0.35rem;
				border-radius: 4px;
				color: var(--text-muted);
				transition: background 100ms;
			}
			.fh-cal__nav-btn:hover { background: var(--bg-color); color: var(--text-color); }
			.fh-cal__month { font-size: var(--text-sm); font-weight: var(--weight-medium); color: var(--text-color); }
			.fh-cal__grid {
				display: grid;
				grid-template-columns: repeat(7, 1fr);
				gap: 1px;
			}
			.fh-cal__dow {
				text-align: center;
				font-size: var(--text-tiny);
				font-weight: var(--weight-regular);
				color: var(--text-muted);
				padding: 0.15rem 0 0.25rem;
			}
			.fh-cal__day {
				text-align: center;
				font-size: var(--text-xs);
				padding: 0.22rem 0;
				border-radius: 4px;
				cursor: pointer;
				color: var(--text-color);
				transition: background 100ms;
			}
			.fh-cal__day:hover { background: var(--bg-color); }
			.fh-cal__day.is-other { color: var(--text-muted); opacity: 0.45; cursor: default; }
			.fh-cal__day.is-other:hover { background: none; }
			.fh-cal__day.is-today { font-weight: var(--weight-medium); color: var(--primary); }
			.fh-cal__day.is-selected { background: var(--primary) !important; color: #fff !important; font-weight: var(--weight-medium); }

			/* Shortcuts strip */
			.fh-due-pop__shortcuts {
				border-top: 1px solid var(--border-color);
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
				font-size: var(--text-xs);
				font-weight: var(--weight-medium);
				color: var(--text-color);
				transition: background 100ms;
				white-space: nowrap;
			}
			.fh-due-pop__short:hover { background: var(--bg-color); }
			.fh-due-pop__short-day { color: var(--text-muted); font-size: var(--text-tiny); margin-left: 0.25rem; }
			.fh-due-pop__clear {
				grid-column: 1 / -1;
				display: flex;
				align-items: center;
				justify-content: center;
				padding: 0.3rem 0.45rem;
				margin-top: 0.05rem;
				border-radius: 5px;
				cursor: pointer;
				font-size: var(--text-xs);
				font-weight: var(--weight-medium);
				color: var(--text-muted);
				transition: background 100ms;
			}
			.fh-due-pop__clear:hover { background: var(--bg-color); color: #dc2626; }

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
				width: 288px;
				padding: 0.35rem;
				display: none;
			}
			.fh-alloc-pop.is-open { display: block; }
			.fh-alloc-pop__results {
				margin-top: 0.25rem;
				display: flex;
				flex-direction: column;
				gap: 0.15rem;
			}
			.fh-alloc-pop__input {
				width: 100%;
				border: 1px solid #e2e8f0;
				border-radius: 5px;
				padding: 0.3rem 0.5rem;
				font-size: var(--text-sm);
				outline: none;
				box-sizing: border-box;
			}
			.fh-alloc-pop__input:focus { border-color: #94a3b8; }
			.fh-alloc-pop__opt {
				display: flex;
				align-items: center;
				gap: 0.4rem;
				padding: 0.32rem 0.45rem;
				border-radius: 5px;
				cursor: pointer;
				font-size: var(--text-sm);
				color: #0f172a;
				transition: background 100ms;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
			}
			.fh-alloc-pop__opt:hover { background: #f8fafc; }
			.fh-alloc-pop__candidate {
				display: flex;
				align-items: center;
				gap: 0.4rem;
				padding: 0.22rem 0.1rem;
			}
			.fh-alloc-pop__candidate-name {
				flex: 1;
				min-width: 0;
				font-size: var(--text-sm);
				color: #0f172a;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
			}
			.fh-alloc-pop__candidate-actions {
				display: flex;
				align-items: center;
				gap: 0.22rem;
				flex-shrink: 0;
			}
			.fh-alloc-pop__assign-btn {
				border: 1px solid #e2e8f0;
				background: #ffffff;
				border-radius: 5px;
				padding: 0.22rem 0.42rem;
				font-size: var(--text-tiny);
				font-weight: var(--weight-medium);
				color: #475569;
				cursor: pointer;
				transition: background 100ms, border-color 100ms, color 100ms;
				white-space: nowrap;
			}
			.fh-alloc-pop__assign-btn:hover {
				background: #f8fafc;
				border-color: #cbd5e1;
			}
			.fh-alloc-pop__assign-btn--main {
				color: #1d4ed8;
				border-color: #bfdbfe;
				background: #eff6ff;
			}
			.fh-alloc-pop__assign-btn--main:hover {
				background: #dbeafe;
				border-color: #93c5fd;
			}
			.fh-alloc-pop__empty {
				padding: 0.4rem 0.45rem;
				font-size: var(--text-xs);
				color: #94a3b8;
				text-align: center;
			}
			.fh-alloc-pop__current-row { display: flex; align-items: center; }
			.fh-alloc-pop__remove {
				flex-shrink: 0;
				padding: 0 0.2rem;
				color: #94a3b8;
				font-size: var(--text-base);
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
			.fh-risk-row[data-risk-key="stale"] .fh-risk-row__value:not(.is-zero)        { color: #7c3aed; }
			.fh-risk-row[data-risk-key="high_priority"] .fh-risk-row__value:not(.is-zero) { color: #dc2626; }
			.fh-risk-row[data-risk-key="no_due_date"] .fh-risk-row__value:not(.is-zero)   { color: #d97706; }
			.fh-risk-row__label {
				flex: 1;
				font-size: var(--text-sm);
				color: #475569;
			}
			.fh-risk-row__value {
				font-size: var(--text-base);
				font-weight: var(--weight-semibold);
				color: #0f172a;
				min-width: 1.4rem;
				text-align: right;
			}
			.fh-risk-row__value.is-zero { color: #cbd5e1; }
			.fh-risk-row__arrow { font-size: var(--text-tiny); color: #cbd5e1; }
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
				font-size: var(--text-tiny);
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
			.fh-sparkline__period {
				font-size: var(--text-tiny);
				color: var(--text-muted);
				text-align: right;
				margin-top: 0.15rem;
			}
			.fh-trow {
				display: flex;
				align-items: center;
				gap: 0.5rem;
				padding: 0.28rem 0;
				font-size: var(--text-sm);
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
				font-size: var(--text-xs);
				font-weight: var(--weight-semibold);
				display: flex;
				align-items: center;
				justify-content: space-between;
				gap: 0.5rem;
			}
			.fh-net__main { flex: 1; text-align: center; }
			.fh-net__prev { font-size: var(--text-tiny); font-weight: var(--weight-medium); opacity: 0.8; white-space: nowrap; }
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
				font-size: var(--text-sm);
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
			@media (max-width: 1180px) {
				.fh-status {
					height: auto;
					min-height: 46px;
					align-items: stretch;
					flex-wrap: nowrap;
					padding: 0 0.3rem;
				}
				.fh-status__msg,
				.fh-status__sep {
					display: none;
				}
				.fh-chips {
					flex: 1 1 0;
					min-width: 0;
					overflow-x: auto;
					overflow-y: hidden;
					padding: 0 0.15rem;
					scrollbar-width: none;
					-ms-overflow-style: none;
				}
				.fh-chips::-webkit-scrollbar { display: none; }
				.fh-status__time {
					flex: 0 0 auto;
					margin-left: auto;
					padding: 0 0.55rem;
					font-size: var(--text-tiny);
					white-space: nowrap;
				}
				.fh-chip {
					padding: 0.28rem 0.48rem;
				}
			}
			@media (max-width: 767px) {
				.fh-queue-layout { display: block; }
				.fh-queue-layout > .fh-panel--queue { border-radius: 10px; }
				.fh-detail__scrim {
					position: fixed;
					inset: 0;
					z-index: 1700;
					display: none;
					border: none;
					margin: 0;
					padding: 0;
					background: rgba(15, 23, 42, 0.2);
				}
				.fh-queue-layout.is-detail-open .fh-detail__scrim { display: block; }
				.fh-detail {
					position: fixed;
					top: 0;
					right: 0;
					bottom: 0;
					width: 100vw;
					max-width: 100vw;
					border-radius: 0;
					border: none;
					border-left: 1px solid var(--border-color);
					transform: translateX(100%);
					opacity: 1;
					pointer-events: auto;
					z-index: 1800;
					transition: transform 260ms ease-in-out;
				}
				.fh-queue-layout.is-detail-open .fh-detail {
					transform: translateX(0);
				}
				.fh-detail__title {
					font-size: var(--text-2xl, 1.65rem);
				}
				.fh-detail__content {
					padding: 0.72rem 0.7rem 0.82rem;
				}
				.fh-detail__line,
				.fh-detail__line-title {
					font-size: var(--text-base);
				}
			}
			@media (max-width: 480px) {
				.fh { padding: 0.5rem; }
				.fh-detail__actions {
					padding: 0.4rem 0.45rem;
				}
				.fh-detail__composer {
					padding: 0.45rem 0.5rem;
				}
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

		const position = (target) => {
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

		const show = (target, tip) => {
			el.textContent = tip;
			el.style.top = "-9999px";
			el.style.left = "0";
			el.classList.add("is-visible");
			position(target);
		};

		const showRich = (target, name, roles) => {
			el.innerHTML = "";
			el.style.top = "-9999px";
			el.style.left = "0";
			const nameEl = document.createElement("div");
			nameEl.className = "fh-tooltip__name";
			nameEl.textContent = name;
			el.appendChild(nameEl);
			if (roles) {
				const rolesEl = document.createElement("div");
				rolesEl.className = "fh-tooltip__roles";
				rolesEl.textContent = roles;
				el.appendChild(rolesEl);
			}
			el.classList.add("is-visible");
			position(target);
		};

		const hide = () => {
			el.classList.remove("is-visible");
			current = null;
		};

		document.addEventListener("mouseover", (e) => {
			const target = e.target.closest("[data-tip], [data-tip-name]");
			if (target === current) return;
			current = target || null;
			if (!target) { hide(); return; }
			const tipName = target.getAttribute("data-tip-name");
			if (tipName) {
				showRich(target, tipName, target.getAttribute("data-tip-roles") || "");
				return;
			}
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

	_setup_realtime_sync() {
		if (!frappe.realtime) return;

		frappe.realtime.doctype_subscribe("ToDo");
		this._on_todo_list_update = (data) => {
			if (!data || data.doctype !== "ToDo") return;
			if (this.loading || this._saving) return;
			clearTimeout(this._realtime_refresh_timer);
			this._realtime_refresh_timer = setTimeout(() => {
				this.refresh({ force: true });
			}, 500);
		};
		frappe.realtime.on("list_update", this._on_todo_list_update);
	}

	refresh({ force = false } = {}) {
		if (this.loading) return;
		this.loading = true;
		this.page.btn_primary?.prop("disabled", true);
		this.render_loading();
		frappe.call({
			method: "opero.todo_dashboard.get_flow_hub_snapshot",
			args: { force_refresh: force ? 1 : 0 },
			callback: (r) => {
				this.loading = false;
				this.page.btn_primary?.prop("disabled", false);
				this.snapshot = r.message || {};
				this._detail_context = {};
				this._detail_loading.clear();
				this._description_draft = null;
				this.render();
			},
			error: () => {
				this.loading = false;
				this.page.btn_primary?.prop("disabled", false);
				this.render_error();
			},
		});
	}

	// ── Main render ──────────────────────────────────────────────────

	render() {
		const s = this.snapshot;
		const tab = this._active_tab;
		let body;
		let activeQueue = [];
		if (tab === "health") {
			this._selected_todo = null;
			body = this._render_health(s.throughput_30d || {}, s.risk || []);
		} else {
			const { queue, title } = this._queue_for_tab(s, tab);
			activeQueue = queue;
			// Deselect if the selected todo is no longer in the current queue
			if (this._selected_todo) {
				const refreshed = queue.find(r => r.name === this._selected_todo.name);
				if (refreshed) {
					this._selected_todo = refreshed;
				} else {
					this._selected_todo = null;
				}
			}
			const queueHtml = this._render_focus_queue(queue, title);
			const queuePanel = `<div class="fh-panel fh-panel--queue"><div class="fh-panel__head"><h2 class="fh-panel__title">${this.esc(title)}</h2></div>${queueHtml}</div>`;
			body = this._selected_todo
				? `<div class="fh-queue-layout">${queuePanel}<button type="button" class="fh-detail__scrim" data-close-detail></button>${this._render_detail(this._selected_todo)}</div>`
				: queuePanel;
		}
		this.$root.html(`
			${this._render_status_bar(s.attention || "", s.updated_at, s.counts || [], s.throughput_30d || {})}
			${body}
		`);
		this._bind_events(s, activeQueue);
		if (this._selected_todo) {
			this._ensure_detail_context(this._selected_todo.name);
			if (this._queue_layout_open_raf) cancelAnimationFrame(this._queue_layout_open_raf);
			this._queue_layout_open_raf = requestAnimationFrame(() => {
				this._queue_layout_open_raf = null;
				this._apply_queue_layout_open_state();
			});
		}
	}

	_apply_queue_layout_open_state() {
		const $layout = this.$root.find(".fh-queue-layout");
		if (!$layout.length) return;
		$layout[0].classList.add("is-detail-open");
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
			stale:        "es-line-clock",
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

		const arrow = trend === "improving" ? "↑" : trend === "worsening" ? "↓" : "→";
		const sign = net > 0 ? "+" : "";
		const tip = `${__("Velocity")}: ${sign}${net} · ${trend}`;

		return `<button type="button" class="fh-chip ${isActive ? "is-active" : ""}"
			data-chip-key="health"
			data-tip="${this.esc(tip)}"
			style="--fh-accent:${accent}">
			<span class="fh-chip__label">${arrow} ${__("Health")}</span>
			<span class="fh-chip__value ${net !== 0 ? "is-nonzero" : ""}">${sign}${net}</span>
		</button>`;
	}

	_render_status_bar(attention, updatedAt, counts, throughput) {
		const msgClass = attention.startsWith("Welcome") ? "is-clear" : "is-ahead";

		const SHORT_LABEL = {
			overdue:     __("Overdue"),
			due_today:   __("Today"),
			due_soon:    __("Soon"),
			in_progress: __("Active"),
			stale:       __("Stale"),
		};

		const countChips = (counts || []).map(c => {
			const isActive = this._active_tab === c.key;
			const isNonZero = c.value > 0;
			const label = SHORT_LABEL[c.key] || c.label || "";
			return `<button type="button" class="fh-chip ${isActive ? "is-active" : ""}"
				data-chip-key="${this.esc(c.key)}"
				style="--fh-accent:${this.esc(c.accent || "var(--primary)")}">
				<span class="fh-chip__label">${this.esc(label)}</span>
				<span class="fh-chip__value ${isNonZero ? "is-nonzero" : ""}">${c.value}</span>
			</button>`;
		}).join("");

		const isActionActive = this._active_tab === "action_queue";
		return `
			<div class="fh-status">
				<span class="fh-status__msg ${msgClass}">${this.esc(attention)}</span>
				<span class="fh-status__sep"></span>
				<div class="fh-chips">
					${countChips}
					${this._render_health_chip(throughput)}
					<button type="button" class="fh-chip ${isActionActive ? "is-active" : ""}"
						data-chip-key="action_queue" style="--fh-accent:#0ea5e9">
						<span class="fh-chip__label">${__("Queue")}</span>
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
						const BAND_SHORT = { overdue: __("Overdue"), due_today: __("Today") };
						const dueBandClass = band !== "active" ? `fh-due-btn--${band}` : "";
						let shortLabel = BAND_SHORT[band] || row.due_label || "";
						if (band === "due_soon" && row.due_date && frappe.datetime && frappe.datetime.get_diff) {
							const daysUntil = Number(frappe.datetime.get_diff(row.due_date, frappe.datetime.get_today()));
							if (Number.isFinite(daysUntil) && daysUntil > 0) {
								shortLabel = __("Due in {0}d", [daysUntil]);
							}
						}
						const tipDate = row.due_date
							? new Date(row.due_date + "T00:00:00").toLocaleDateString(undefined, {
								weekday: "short", month: "short", day: "numeric",
							  })
							: "";
						const tipDetail = row.due_label || "";
						const dueLabel = shortLabel
							? `<span role="button" class="fh-due-btn ${dueBandClass}" data-due-todo="${this.esc(row.name)}" data-due-date="${this.esc(row.due_date || '')}"${tipDetail ? ` data-tip-name="${this.esc(tipDetail)}"` : ""}${tipDate ? ` data-tip-roles="${this.esc(tipDate)}"` : ""}>${this.esc(shortLabel)}</span>`
							: `<span role="button" class="fh-due-btn fh-due-btn--empty" data-due-todo="${this.esc(row.name)}" data-due-date="" title="${this.esc(__('Set due date'))}">📅</span>`;
						const avatars = this._render_avatars(row.assignees, row.name);
						const pc = this._prio_config(row.priority);
						const prioTip = this.esc(row.priority || __("Priority"));
						const isSelected = this._selected_todo?.name === row.name;
						return `
						<button type="button" class="fh-item fh-band-${band}${isSelected ? " is-selected" : ""}" data-queue-index="${i}">
							<span role="button" class="fh-prio-btn" aria-label="${prioTip}" data-tip="${prioTip}" data-prio-index="${i}" data-todo-name="${this.esc(row.name)}" style="color:${pc.color}">${pc.icon}</span>
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
				<div class="fh-risk-row" data-risk-index="${i}" data-risk-key="${this.esc(r.key || "")}" role="button">
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
				<div class="fh-risk-row" data-risk-index="${i}" data-risk-key="${this.esc(r.key || "")}" role="button">
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
		const days = (dailyClosed && dailyClosed.length) ? dailyClosed : Array(30).fill(0);
		const maxVal = Math.max(...days, 1);
		const W = 200;
		const H = 40;
		const n = days.length;

		const pts = days.map((v, i) => {
			const x = n > 1 ? (i / (n - 1)) * W : 0;
			const y = H - (v / maxVal) * (H - 4);
			return [+x.toFixed(1), +y.toFixed(1)];
		});

		const lineD = pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x},${y}`).join(" ");
		const areaD = `${lineD} L${W},${H} L0,${H} Z`;

		return `
			<div class="fh-sparkline-wrap">
				<svg class="fh-sparkline" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
					<path d="${areaD}" fill="#059669" fill-opacity="0.15"/>
					<path d="${lineD}" fill="none" stroke="#059669" stroke-width="1.5" stroke-linejoin="round"/>
				</svg>
				<div class="fh-sparkline__period">30d</div>
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

	_bind_events(s, queue = []) {
		const counts = s.counts || [];
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
				if (!this._selected_todo) this._description_draft = null;
				this.render();
				if (this._selected_todo?.name) {
					this._ensure_detail_context(this._selected_todo.name);
				}
			});
		});

		this.$root.find("[data-close-detail]").on("click", () => {
			this._selected_todo = null;
			this._description_draft = null;
			this.render();
		});

		this.$root.find("[data-prio-index], [data-detail-prio]").on("click", (e) => {
			e.stopPropagation();
			this._open_prio_dropdown(e.currentTarget);
		});

		this.$root.find("[data-detail-action='done']").on("click", (e) => {
			e.stopPropagation();
			const todoName = $(e.currentTarget).attr("data-todo-name");
			if (!todoName) return;
			this._mark_todo_done(todoName);
		});

		this.$root.find("[data-add-alloc]").on("click", (e) => {
			e.stopPropagation();
			this._open_assignee_popover(e.currentTarget);
		});

		this.$root.find("[data-due-todo]").on("click", (e) => {
			e.stopPropagation();
			this._open_due_date_popover(e.currentTarget);
		});

		this.$root.find("[data-detail-open-beneficiary]").on("click", (e) => {
			if ($(e.target).closest("[data-detail-clear-beneficiary]").length) return;
			e.preventDefault();
			e.stopPropagation();
			const $el = $(e.currentTarget);
			const todoName = $el.attr("data-detail-open-beneficiary");
			const current  = $el.attr("data-current-beneficiary") || "";
			if (todoName) this._open_link_combobox(todoName, $el, current, "User", (val) => {
				this._save_field(todoName, { custom_owner: val });
			});
		});

		this.$root.find("[data-detail-clear-beneficiary]").on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			const todoName = $(e.currentTarget).attr("data-todo-name");
			if (todoName) this._save_field(todoName, { custom_owner: "" });
		});

		this.$root.find("[data-detail-add-assignee]").on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			const todoName = $(e.currentTarget).attr("data-detail-add-assignee");
			if (!todoName) return;
			const row = (this.snapshot.focus_queue || []).find(r => r.name === todoName);
			const existing = new Set(((row && row.assignees) || []).map(a => a.user));
			this._open_add_assignee_dropdown(todoName, $(e.currentTarget), existing);
		});

		this.$root.find("[data-remove-assignee]").on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			const user     = $(e.currentTarget).attr("data-remove-assignee");
			const todoName = $(e.currentTarget).attr("data-todo-name");
			if (!user || !todoName) return;
			this._saving++;
			frappe.call({
				method:   "opero.todo_dashboard.remove_todo_assignee",
				args:     { todo_name: todoName, user, expected_modified: this._row_modified(todoName) },
				callback: () => this._on_save_done(),
				error:    () => this._on_save_error(),
			});
		});

		this.$root.find("[data-promote-assignee]").on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			if ($(e.currentTarget).closest(".fh-member-chip.is-main").length) return;
			const user     = $(e.currentTarget).attr("data-promote-assignee");
			const todoName = $(e.currentTarget).attr("data-todo-name");
			if (!user || !todoName) return;
			this._saving++;
			frappe.call({
				method:   "opero.todo_dashboard.add_todo_assignee",
				args:     { todo_name: todoName, user, as_main_assignee: 1, expected_modified: this._row_modified(todoName) },
				callback: () => this._on_save_done(),
				error:    () => this._on_save_error(),
			});
		});

		this.$root.find("[data-detail-open-project]").on("click", (e) => {
			if ($(e.target).closest("[data-detail-clear-project]").length) return;
			e.preventDefault();
			e.stopPropagation();
			const $el = $(e.currentTarget);
			const todoName = $el.attr("data-detail-open-project");
			const currentProject = $el.attr("data-current-project") || "";
			if (todoName) this._open_project_combobox(todoName, $el, currentProject);
		});

		this.$root.find("[data-detail-clear-project]").on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			const todoName = $(e.currentTarget).attr("data-todo-name");
			if (todoName) this._save_project_reference(todoName, "");
		});

		this.$root.find("[data-detail-edit-desc]").on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			const todoName = $(e.currentTarget).attr("data-detail-edit-desc");
			if (todoName) this._start_description_edit(todoName);
		});

		this.$root.find("[data-detail-desc-cancel]").on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			this._description_draft = null;
			this.render();
		});

		this.$root.find("[data-detail-desc-save]").on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			const todoName = $(e.currentTarget).attr("data-detail-desc-save");
			if (todoName) this._save_description_edit(todoName);
		});

		this.$root.find("[data-detail-desc-input]").on("input", (e) => {
			if (!this._description_draft) return;
			this._description_draft.value = $(e.currentTarget).val();
		});

		this.$root.find("[data-detail-add-attachment]").on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			const todoName = $(e.currentTarget).attr("data-detail-add-attachment");
			if (todoName) this._upload_todo_attachment(todoName);
		});

		this.$root.find("[data-detail-remove-attachment]").on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			const todoName = $(e.currentTarget).attr("data-todo-name");
			const fileId = $(e.currentTarget).attr("data-detail-remove-attachment");
			if (todoName && fileId) this._remove_todo_attachment(todoName, fileId);
		});

		this.$root.find("[data-detail-edit-field]").on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			const todoName = $(e.currentTarget).attr("data-detail-edit-field");
			if (!todoName) return;
			const detail = this._detail_context[todoName] || {};
			this._open_custom_field_dialog(todoName, detail.field_values || {});
		});

		this.$root.find("[data-detail-comment-input]").on("keydown", (e) => {
			if (e.key !== "Enter" || e.shiftKey) return;
			e.preventDefault();
			const todoName = $(e.currentTarget).attr("data-detail-comment-input");
			if (todoName) this._post_detail_comment(todoName, $(e.currentTarget));
		});

		this.$root.find("[data-detail-comment-send]").on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			const todoName = $(e.currentTarget).attr("data-detail-comment-send");
			if (!todoName) return;
			const $input = this.$root.find(`[data-detail-comment-input="${todoName}"]`).first();
			this._post_detail_comment(todoName, $input);
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
				<span role="button" tabindex="0" class="fh-add-alloc" data-tip="${this.esc(__("Add Member"))}" ${nameAttr}>
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
			const roles = (a.roles || []).join(" · ");
			const tipName = `data-tip-name="${this.esc(a.full_name)}"`;
			const tipRoles = roles ? `data-tip-roles="${this.esc(roles)}"` : "";
			if (a.image) {
				return `<span ${tipName} ${tipRoles}><span class="fh-avatar"><img src="${this.esc(a.image)}" alt="${this.esc(a.initials)}"></span></span>`;
			}
			return `<span ${tipName} ${tipRoles}><span class="fh-avatar" style="background:${_color(a.user)}">${this.esc(a.initials)}</span></span>`;
		}).join("");
		const overflowNames = assignees.slice(MAX).map(a => a.full_name || a.user).join(", ");
		const more = extra > 0 ? `<span class="fh-avatar-more"${overflowNames ? ` data-tip="${this.esc(overflowNames)}"` : ""}>+${extra}</span>` : "";
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
				<input type="text" class="fh-alloc-pop__input" placeholder="${__("Add member…")}">
				<div class="fh-alloc-pop__results"></div>
			</div>`).appendTo(document.body);

			$pop.on("input", ".fh-alloc-pop__input", (e) => {
				const name = $($pop.data("active-btn")).attr("data-add-alloc");
				const row = (this.snapshot.focus_queue || []).find(r => r.name === name);
				const existing = new Set(((row && row.assignees) || []).map(a => a.user));
				this._search_assignee_users($(e.target).val(), $pop, existing);
			});

			$pop.on("click", ".fh-alloc-pop__assign-btn[data-user]", (e) => {
				e.stopPropagation();
				const user = $(e.currentTarget).attr("data-user");
				const fullName = $(e.currentTarget).attr("data-full-name") || user || "";
				const image = $(e.currentTarget).attr("data-user-image") || "";
				const name = $($pop.data("active-btn")).attr("data-add-alloc");
				const addRole = $(e.currentTarget).attr("data-add-role") || "assignee";
				if (!user || !name) return;
				$pop.removeClass("is-open");
				this._apply_local_assignee_update(name, {
					user,
					full_name: fullName,
					image,
					initials: this._initials(fullName || user),
					roles: [],
				}, addRole);
				this._saving++;
				frappe.call({
					method: "opero.todo_dashboard.add_todo_assignee",
					args: {
						todo_name: name,
						user,
						as_main_assignee: addRole === "main" ? 1 : 0,
						expected_modified: this._row_modified(name),
					},
					callback: () => this._on_save_done(),
					error: () => this._on_save_error(),
				});
			});

			$pop.on("click", ".fh-alloc-pop__remove", (e) => {
				e.stopPropagation();
				const user = $(e.currentTarget).attr("data-user");
				const name = $($pop.data("active-btn")).attr("data-add-alloc");
				if (!user || !name) return;
				$pop.removeClass("is-open");
				this._saving++;
				frappe.call({
					method: "opero.todo_dashboard.remove_todo_assignee",
					args: { todo_name: name, user, expected_modified: this._row_modified(name) },
					callback: () => this._on_save_done(),
					error: () => this._on_save_error(),
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
		$pop.attr("data-has-assignees", current.length ? "1" : "0");

		const rect = btn.getBoundingClientRect();
		const popWidth = $pop.outerWidth() || 288;
		$pop.css({ top: rect.bottom + 4, left: Math.max(4, rect.right - popWidth) });
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
				fields: ["name", "full_name", "user_image"],
				limit_page_length: 8,
			},
			callback: (r) => {
				const users = (r.message || []).filter(u => !excludeSet.has(u.name));
				const $results = $pop.find(".fh-alloc-pop__results").empty();
				const hasAssignees = $pop.attr("data-has-assignees") === "1";
				if (!users.length) {
					$results.html(`<div class="fh-alloc-pop__empty">${__("No users found")}</div>`);
					return;
				}
					users.forEach(u => {
						const name = this.esc(u.full_name || u.name);
						const user = this.esc(u.name);
						const image = this.esc(u.user_image || "");
						const assigneeBtn = hasAssignees
							? `<button type="button" class="fh-alloc-pop__assign-btn" data-user="${user}" data-full-name="${name}" data-user-image="${image}" data-add-role="assignee">${__("Assignee")}</button>`
							: "";
						const mainLabel = hasAssignees ? __("Main") : __("Main Assignee");
						$results.append(`
							<div class="fh-alloc-pop__candidate">
								<span class="fh-alloc-pop__candidate-name">${name}</span>
								<span class="fh-alloc-pop__candidate-actions">
									${assigneeBtn}
									<button type="button" class="fh-alloc-pop__assign-btn fh-alloc-pop__assign-btn--main" data-user="${user}" data-full-name="${name}" data-user-image="${image}" data-add-role="main">${this.esc(mainLabel)}</button>
								</span>
							</div>
						`);
					});
				},
			});
	}

	_initials(name) {
		const parts = String(name || "").trim().split(/\s+/).filter(Boolean);
		if (!parts.length) return "?";
		if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
		return `${parts[0][0] || ""}${parts[parts.length - 1][0] || ""}`.toUpperCase();
	}

	_retag_assignees(assignees) {
		const mainLabel = __("Main Assignee");
		const assigneeLabel = __("Assignee");
		return (assignees || []).map((a, idx) => {
			const preserved = (a.roles || []).filter(role => role !== mainLabel && role !== assigneeLabel);
			return {
				...a,
				roles: [...preserved, idx === 0 ? mainLabel : assigneeLabel],
			};
		});
	}

	_apply_local_assignee_update(todoName, assignee, addRole) {
		const queue = this.snapshot.focus_queue || [];
		const row = queue.find(item => item.name === todoName);
		if (!row) return;

		const current = Array.isArray(row.assignees) ? [...row.assignees] : [];
		const existingIndex = current.findIndex(item => item.user === assignee.user);
		if (existingIndex >= 0) {
			current.splice(existingIndex, 1);
		}

		if (addRole === "main") {
			current.unshift(assignee);
		} else if (existingIndex === -1) {
			current.push(assignee);
		} else {
			current.splice(existingIndex, 0, assignee);
		}

		const updated = this._retag_assignees(current);
		row.assignees = updated;
		if (this._selected_todo?.name === todoName) {
			this._selected_todo.assignees = updated;
		}
		this.render();
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
						<span class="fh-prio-drop__check">✓</span>
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
				this._saving++;
				frappe.call({
					method: "opero.todo_dashboard.update_todo_from_flow_hub",
					args: {
						todo_name: todoName,
						values: { priority: newPrio },
						expected_modified: this._row_modified(todoName),
					},
					callback: () => this._on_save_done(),
					error: () => this._on_save_error(),
				});
			});
		}

		if ($drop.hasClass("is-open") && $drop.data("active-btn") === btn) {
			$drop.removeClass("is-open");
			return;
		}

		const todoName = $(btn).attr("data-todo-name");
		const row = (this.snapshot.focus_queue || []).find(r => r.name === todoName);
		const currentPrio = row?.priority || "";
		$drop.find(".fh-prio-drop__opt").each((_, el) => {
			$(el).toggleClass("is-current", $(el).attr("data-prio-value") === currentPrio);
		});

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
			$sc.append(`<div class="fh-due-pop__short" data-due-days="${s.days}">
				${this.esc(s.label)}
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

	_ensure_detail_context(todoName, { force = false } = {}) {
		if (!todoName) return;
		if (!force && this._detail_context[todoName]) return;
		if (this._detail_loading.has(todoName)) return;

		this._detail_loading.add(todoName);
		if (this._selected_todo?.name === todoName) {
			this.render();
		}
		frappe.call({
			method: "opero.todo_dashboard.get_todo_detail_context",
			args: { todo_name: todoName },
			callback: (r) => {
				this._detail_loading.delete(todoName);
				this._detail_context[todoName] = r.message || {};
				if (this._selected_todo?.name === todoName) {
					this.render();
				}
			},
			error: () => {
				this._detail_loading.delete(todoName);
				if (this._selected_todo?.name === todoName) {
					this.render();
				}
			},
		});
	}

	_start_description_edit(todoName) {
		const detail = this._detail_context[todoName] || {};
		const fallback = (this._selected_todo?.description || "").trim();
		this._description_draft = {
			todoName,
			value: String(detail.description || fallback || ""),
		};
		this.render();
	}

	_save_description_edit(todoName) {
		if (!this._description_draft || this._description_draft.todoName !== todoName) return;
		const nextValue = String(this._description_draft.value || "").trim();
		this._description_draft = null;
		this._saving++;
		frappe.call({
			method: "opero.todo_dashboard.update_todo_from_flow_hub",
			args: {
				todo_name: todoName,
				values: { description: nextValue || null },
				expected_modified: this._row_modified(todoName),
			},
			callback: () => this._on_save_done(),
			error: () => this._on_save_error(),
		});
	}

	_open_project_combobox(todoName, $field, currentProject = "") {
		this._open_link_combobox(todoName, $field, currentProject, "Project", (val) => {
			this._save_project_reference(todoName, val);
		});
	}

	_open_link_combobox(todoName, $field, currentValue = "", doctype, onSelect) {
		$field.addClass("is-open");
		const $body = $field.find(".fh-field-outlined__body");
		$body.html(`<input class="fh-project-input" type="text" value="${this.esc(currentValue)}" placeholder="${__("Search…")}" autocomplete="off" spellcheck="false">`);
		const $input = $body.find(".fh-project-input").focus().select();

		const $drop = $("<ul class='fh-project-dropdown'></ul>").appendTo(document.body);
		let results = [], focusIdx = -1, _timer;

		const _position = () => {
			const r = $field[0].getBoundingClientRect();
			$drop.css({ top: r.bottom + 3, left: r.left, width: r.width });
		};
		_position();

		const _highlight = () => {
			$drop.find(".fh-project-dropdown__item").removeClass("is-focused").eq(focusIdx).addClass("is-focused");
		};

		const _render_results = (rows) => {
			results = rows; focusIdx = -1;
			$drop.html(results.length
				? results.map((v, i) => `<li class="fh-project-dropdown__item" data-idx="${i}">${this.esc(v)}</li>`).join("")
				: `<li class="fh-project-dropdown__empty">${__("No matches")}</li>`
			);
		};

		const _search = (txt) => {
			clearTimeout(_timer);
			_timer = setTimeout(() => {
				frappe.call({
					method: "frappe.desk.search.search_link",
					args: { txt, doctype, ignore_user_permissions: 0, reference_doctype: "ToDo", page_length: 10 },
					callback: (r) => {
						const rows = (r.message || []).map(x => (typeof x === "string" ? x : x.value) || "").filter(Boolean);
						_render_results(rows);
					},
				});
			}, 180);
		};

		const ns = "mousedown.fh_link_" + doctype;
		const _cleanup = () => { clearTimeout(_timer); $drop.remove(); $(document).off(ns); };
		const _cancel  = () => { _cleanup(); this.render(); };
		const _select  = (val) => { _cleanup(); onSelect(val); };

		$input.on("input", (e) => _search(e.target.value));
		$input.on("keydown", (e) => {
			if (e.key === "Escape") { _cancel(); return; }
			if (e.key === "ArrowDown") { focusIdx = Math.min(focusIdx + 1, results.length - 1); _highlight(); e.preventDefault(); return; }
			if (e.key === "ArrowUp")   { focusIdx = Math.max(focusIdx - 1, 0); _highlight(); e.preventDefault(); return; }
			if (e.key === "Enter") {
				const pick = focusIdx >= 0 ? results[focusIdx] : (results.length === 1 ? results[0] : null);
				if (pick) _select(pick);
				e.preventDefault();
			}
		});
		$drop.on("mousedown", ".fh-project-dropdown__item", (e) => {
			e.preventDefault();
			const idx = parseInt($(e.currentTarget).attr("data-idx"), 10);
			if (results[idx]) _select(results[idx]);
		});
		$(document).on(ns, (e) => {
			if (!$field[0].contains(e.target) && !$drop[0].contains(e.target)) _cancel();
		});
		_search(currentValue);
	}

	_open_add_assignee_dropdown(todoName, $btn, excludeUsers = new Set()) {
		const $drop = $(`<div class="fh-project-dropdown" style="padding:0.3rem">
			<input class="fh-project-input" style="border:1px solid var(--border-color);border-radius:4px;padding:0.22rem 0.4rem;width:100%;box-sizing:border-box"
				type="text" placeholder="${__("Search user…")}" autocomplete="off" spellcheck="false">
			<ul class="fh-assignee-drop__list" style="margin:0.25rem 0 0;padding:0;list-style:none"></ul>
		</div>`).appendTo(document.body);

		const r = $btn[0].getBoundingClientRect();
		$drop.css({ position: "fixed", top: r.bottom + 3, left: r.left, width: Math.max(r.width, 180) });

		const $input = $drop.find("input").focus();
		const $list  = $drop.find(".fh-assignee-drop__list");
		let results = [], focusIdx = -1, _timer;

		const _highlight = () => {
			$list.find(".fh-project-dropdown__item").removeClass("is-focused").eq(focusIdx).addClass("is-focused");
		};

		const _render = (rows) => {
			results = rows.filter(v => !excludeUsers.has(v.value || v));
			focusIdx = -1;
			$list.html(results.length
				? results.map((v, i) => `<li class="fh-project-dropdown__item" data-idx="${i}">${this.esc(v.label || v.value || v)}</li>`).join("")
				: `<li class="fh-project-dropdown__empty">${__("No matches")}</li>`
			);
		};

		const _search = (txt) => {
			clearTimeout(_timer);
			_timer = setTimeout(() => {
				frappe.call({
					method: "frappe.desk.search.search_link",
					args: { txt, doctype: "User", ignore_user_permissions: 0, reference_doctype: "ToDo", page_length: 10,
						filters: JSON.stringify({ user_type: "System User", name: ["!=", "Guest"] }) },
					callback: (res) => {
						_render(res.message || []);
					},
				});
			}, 180);
		};

		const _cleanup = () => { clearTimeout(_timer); $drop.remove(); $(document).off("mousedown.fh_add_assignee"); };

		const _select = (item) => {
			_cleanup();
			const user = item.value || item;
			this._saving++;
			frappe.call({
				method:   "opero.todo_dashboard.add_todo_assignee",
				args:     { todo_name: todoName, user, as_main_assignee: 0, expected_modified: this._row_modified(todoName) },
				callback: () => this._on_save_done(),
				error:    () => this._on_save_error(),
			});
		};

		$input.on("input", (e) => _search(e.target.value));
		$input.on("keydown", (e) => {
			if (e.key === "Escape") { _cleanup(); return; }
			if (e.key === "ArrowDown") { focusIdx = Math.min(focusIdx + 1, results.length - 1); _highlight(); e.preventDefault(); return; }
			if (e.key === "ArrowUp")   { focusIdx = Math.max(focusIdx - 1, 0); _highlight(); e.preventDefault(); return; }
			if (e.key === "Enter") {
				const pick = focusIdx >= 0 ? results[focusIdx] : (results.length === 1 ? results[0] : null);
				if (pick) _select(pick);
				e.preventDefault();
			}
		});
		$list.on("mousedown", ".fh-project-dropdown__item", (e) => {
			e.preventDefault();
			const idx = parseInt($(e.currentTarget).attr("data-idx"), 10);
			if (results[idx]) _select(results[idx]);
		});
		$(document).on("mousedown.fh_add_assignee", (e) => {
			if (!$drop[0].contains(e.target) && !$btn[0].contains(e.target)) _cleanup();
		});
		_search("");
	}

	_save_field(todoName, values) {
		this._saving++;
		frappe.call({
			method: "opero.todo_dashboard.update_todo_from_flow_hub",
			args: { todo_name: todoName, values, expected_modified: this._row_modified(todoName) },
			callback: () => this._on_save_done(),
			error:    () => this._on_save_error(),
		});
	}

	_save_project_reference(todoName, projectName) {
		const cleanProject = String(projectName || "").trim();
		const values = cleanProject
			? { reference_type: "Project", reference_name: cleanProject }
			: { reference_type: null, reference_name: null };
		this._saving++;
		frappe.call({
			method: "opero.todo_dashboard.update_todo_from_flow_hub",
			args: {
				todo_name: todoName,
				values,
				expected_modified: this._row_modified(todoName),
			},
			callback: () => this._on_save_done(),
			error: () => this._on_save_error(),
		});
	}

	_upload_todo_attachment(todoName) {
		new frappe.ui.FileUploader({
			doctype: "ToDo",
			docname: todoName,
			folder: "Home/Attachments",
			on_success: () => {
				frappe.show_alert({ message: __("Attachment added"), indicator: "green" }, 2);
				this._ensure_detail_context(todoName, { force: true });
			},
		});
	}

	_remove_todo_attachment(todoName, fileId) {
		frappe.call({
			method: "frappe.desk.form.utils.remove_attach",
			type: "DELETE",
			args: {
				fid: fileId,
				dt: "ToDo",
				dn: todoName,
			},
			callback: () => {
				frappe.show_alert({ message: __("Attachment removed"), indicator: "green" }, 2);
				this._ensure_detail_context(todoName, { force: true });
			},
		});
	}

	_editable_todo_fields() {
		return [
			{ fieldname: "reference_type", label: __("Reference Type") },
			{ fieldname: "reference_name", label: __("Reference Name") },
			{ fieldname: "role", label: __("Role") },
			{ fieldname: "color", label: __("Color") },
			{ fieldname: "sender", label: __("Sender") },
			{ fieldname: "assignment_rule", label: __("Assignment Rule") },
		];
	}

	_open_custom_field_dialog(todoName, fieldValues = {}) {
		const defs = this._editable_todo_fields();
		const options = defs.map(def => `${def.label} (${def.fieldname})`);
		const first = defs[0];
		const dialog = new frappe.ui.Dialog({
			title: __("Add or Edit Field"),
			fields: [
				{
					fieldtype: "Select",
					fieldname: "field_option",
					label: __("Field"),
					reqd: 1,
					options: options.join("\n"),
					default: `${first.label} (${first.fieldname})`,
				},
				{
					fieldtype: "Data",
					fieldname: "field_value",
					label: __("Value"),
				},
				{
					fieldtype: "Check",
					fieldname: "clear_value",
					label: __("Clear value"),
					default: 0,
				},
			],
			primary_action_label: __("Save"),
			primary_action: (values) => {
				const def = defs.find(d => `${d.label} (${d.fieldname})` === values.field_option);
				if (!def) return;
				const value = values.clear_value ? null : values.field_value;
				dialog.hide();
				this._saving++;
				frappe.call({
					method: "opero.todo_dashboard.update_todo_from_flow_hub",
					args: {
						todo_name: todoName,
						values: { [def.fieldname]: value },
						expected_modified: this._row_modified(todoName),
					},
					callback: () => this._on_save_done(),
					error: () => this._on_save_error(),
				});
			},
		});

		const syncValue = () => {
			const selected = dialog.get_value("field_option");
			const def = defs.find(d => `${d.label} (${d.fieldname})` === selected) || first;
			dialog.set_value("field_value", fieldValues[def.fieldname] || "");
			dialog.set_value("clear_value", 0);
		};

		dialog.show();
		dialog.fields_dict.field_option.$input.on("change", syncValue);
		syncValue();
	}

	_post_detail_comment(todoName, $input) {
		if (!$input || !$input.length) return;
		const content = String($input.val() || "").trim();
		if (!content) return;
		frappe.call({
			method: "frappe.desk.form.utils.add_comment",
			args: {
				reference_doctype: "ToDo",
				reference_name: todoName,
				content,
				comment_email: frappe.session.user_email || frappe.session.user,
				comment_by: frappe.session.user_fullname || frappe.session.user,
			},
			callback: () => {
				$input.val("");
				frappe.show_alert({ message: __("Comment added"), indicator: "green" }, 2);
				this._ensure_detail_context(todoName, { force: true });
			},
		});
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

	_on_save_done() {
		this._saving = Math.max(0, this._saving - 1);
		if (this._saving === 0) {
			frappe.show_alert({ message: __("Saved"), indicator: "green" }, 2);
			this.refresh({ force: true });
		}
	}

	_on_save_error() {
		this._saving = Math.max(0, this._saving - 1);
		this.refresh({ force: true });
	}

	_save_due_date(todoName, date) {
		this._saving++;
		frappe.call({
			method: "opero.todo_dashboard.update_todo_from_flow_hub",
			args: {
				todo_name: todoName,
				values: { date: date || null },
				expected_modified: this._row_modified(todoName),
			},
			callback: () => this._on_save_done(),
			error: () => this._on_save_error(),
		});
	}

	_mark_todo_done(todoName) {
		this._saving++;
		frappe.call({
			method: "opero.todo_dashboard.update_todo_from_flow_hub",
			args: {
				todo_name: todoName,
				values: { status: "Closed" },
				expected_modified: this._row_modified(todoName),
			},
			callback: () => this._on_save_done(),
			error: () => this._on_save_error(),
		});
	}

	_row_modified(todoName) {
		const row = (this.snapshot.focus_queue || []).find(r => r.name === todoName);
		return row?.modified || "";
	}

	_render_detail(todo) {
		const name      = todo.name || "";
		const title     = todo.title || todo.name || "";
		const status    = todo.status || "";
		const priority  = todo.priority || "";
		const dueLabel  = todo.due_label || "";
		const dueDate   = todo.due_date || "";
		const band      = todo.urgency_band || "";
		const dueBandClass = band && band !== "active" ? `fh-due-btn--${band}` : "";
		const assignees = todo.assignees || [];
		const detail = this._detail_context[name] || {};
		const isLoading = this._detail_loading.has(name);
		const attachments = Array.isArray(detail.attachments) ? detail.attachments : [];
		const activity = Array.isArray(detail.activity) ? detail.activity : [];
		const fieldValues = detail.field_values || {};
		const referenceType = String(fieldValues.reference_type || "").trim();
		const referenceName = String(fieldValues.reference_name || "").trim();
		const projectName = referenceType === "Project" ? referenceName : "";
		const priorityPc = this._prio_config(priority);

		const isEditingDesc = this._description_draft?.todoName === name;
		const descValue = isEditingDesc
			? this._description_draft.value
			: String(detail.description || todo.description || "").trim();
		const hasDesc = Boolean(String(descValue || "").trim());

		const mainAssignee = assignees.find(a => Array.isArray(a.roles) && a.roles.includes(__("Main Assignee"))) || assignees[0] || null;

		const creatorName     = String(detail.creator_name     || "").trim();
		const beneficiaryUser = String(detail.beneficiary_user || "").trim();
		const beneficiaryName = String(detail.beneficiary_name || "").trim();

		const assigneeChipsHtml = assignees.map(a => {
			const isMain = a === mainAssignee;
			return `<span class="fh-member-chip ${isMain ? "is-main" : ""}">
				<button type="button" class="fh-member-chip__promote"
					data-promote-assignee="${this.esc(a.user)}"
					data-todo-name="${this.esc(name)}"
					title="${isMain ? __("Main assignee") : __("Set as main")}">
					${isMain ? "◆" : "◇"}
				</button>
				<span class="fh-member-chip__name">${this.esc(a.full_name || a.user)}</span>
				<button type="button" class="fh-member-chip__remove"
					data-remove-assignee="${this.esc(a.user)}"
					data-todo-name="${this.esc(name)}"
					title="${__("Remove")}">×</button>
			</span>`;
		}).join("");

		const attachmentList = attachments.length
			? attachments.map(file => `
				<div class="fh-detail__attachment">
					<a class="fh-detail__attachment-link" href="${this.esc(file.file_url || "#")}" target="_blank" rel="noopener">${this.esc(file.file_name || file.name || __("Attachment"))}</a>
					<button type="button" class="fh-detail__attachment-remove" data-detail-remove-attachment="${this.esc(file.name)}" data-todo-name="${this.esc(name)}" title="${__("Remove")}">×</button>
				</div>
			`).join("")
			: `<div class="fh-detail__line-sub">${this.esc(__("No attachments"))}</div>`;

		const fieldDefs = this._editable_todo_fields();
		const fieldSummary = Object.entries(fieldValues)
			.filter(([fieldname]) => !["reference_type", "reference_name"].includes(fieldname))
			.map(([fieldname, value]) => {
				const def = fieldDefs.find(item => item.fieldname === fieldname);
				const label = def ? def.label : fieldname;
				return `<span class="fh-detail__tag">${this.esc(label)}: ${this.esc(String(value || ""))}</span>`;
			})
			.join("");

		const activityHtml = activity.length
			? activity.map(entry => `
				<div class="fh-detail__activity-item">
					<div class="fh-detail__activity-head">
						<span class="fh-detail__activity-type">${this.esc(entry.type || __("Comment"))}</span>
						<span>${this.esc(entry.by || __("Unknown"))}</span>
						<span>·</span>
						<span>${this.esc(this._fmt_time_text(entry.creation) || "")}</span>
					</div>
					<div class="fh-detail__activity-content">${this.esc(entry.content || "")}</div>
				</div>
			`).join("")
			: `<div class="fh-detail__activity-empty">${this.esc(__("No activity yet"))}</div>`;

		return `<div class="fh-detail">
			<div class="fh-detail__actions">
				<a class="fh-detail__action-btn is-link" href="/app/todo/${this.esc(name)}">${__("Open in form")} ↗</a>
				<span class="fh-detail__action-spacer"></span>
				<button type="button" class="fh-detail__action-btn" data-due-todo="${this.esc(name)}" data-due-date="${this.esc(dueDate)}">${dueDate ? __("Due") : __("Set due")}</button>
				<button type="button" class="fh-detail__action-btn" data-detail-prio="1" data-todo-name="${this.esc(name)}">${this.esc(priorityPc.icon)} ${this.esc(priority || __("Priority"))}</button>
				<button type="button" class="fh-detail__action-btn is-primary" data-detail-action="done" data-todo-name="${this.esc(name)}">${__("Mark done")}</button>
				<button type="button" class="fh-detail__action-btn is-quiet" data-close-detail title="${__("Close")}">✕</button>
			</div>
			<div class="fh-detail__content">
				<div class="fh-detail__title-wrap">
					<button type="button" class="fh-detail__checkbox" data-detail-action="done" data-todo-name="${this.esc(name)}" title="${__("Mark done")}">○</button>
					<h3 class="fh-detail__title">${this.esc(title)}</h3>
				</div>
				<div class="fh-detail__meta">
					${dueLabel
						? `<button type="button" class="fh-detail__meta-chip is-due fh-due-btn ${dueBandClass}" data-due-todo="${this.esc(name)}" data-due-date="${this.esc(dueDate)}">${this.esc(dueLabel)}</button>`
						: `<button type="button" class="fh-detail__meta-chip is-due fh-due-btn fh-due-btn--empty" data-due-todo="${this.esc(name)}" data-due-date="">${__("Set due")}</button>`
					}
					<span class="fh-detail__meta-chip is-quiet">${this.esc(status || __("Open"))}</span>
					<span class="fh-detail__meta-chip is-quiet">${this.esc(priority || __("No priority"))}</span>
				</div>
				<hr class="fh-detail__divider">

				<div class="fh-detail__section">
					<div class="fh-members__grid">
						<div class="fh-field-outlined">
							<span class="fh-field-outlined__label">${this.esc(__("Creator"))}</span>
							<div class="fh-field-outlined__body">
								<span class="fh-field-outlined__value ${creatorName ? "" : "is-empty"}">${this.esc(creatorName)}</span>
							</div>
						</div>
						<div class="fh-field-outlined fh-field-outlined--clickable"
							data-detail-open-beneficiary="${this.esc(name)}"
							data-current-beneficiary="${this.esc(beneficiaryUser)}">
							<span class="fh-field-outlined__label">${this.esc(__("Beneficiary"))}</span>
							<div class="fh-field-outlined__body">
								<span class="fh-field-outlined__value ${beneficiaryName ? "" : "is-empty"}">${this.esc(beneficiaryName)}</span>
								${beneficiaryName
									? `<button type="button" class="fh-field-outlined__clear" data-detail-clear-beneficiary="1" data-todo-name="${this.esc(name)}" title="${__("Clear")}">×</button>`
									: ""}
							</div>
						</div>
					</div>
					<div class="fh-field-outlined">
						<span class="fh-field-outlined__label">${this.esc(__("Assignee(s)"))}</span>
						<div class="fh-members__chips">
							${assigneeChipsHtml}
							<button type="button" class="fh-members__add-btn" data-detail-add-assignee="${this.esc(name)}">+ ${__("Add")}</button>
						</div>
					</div>
				</div>

				<div class="fh-detail__section">
					<div class="fh-field-outlined fh-field-outlined--clickable"
						data-detail-open-project="${this.esc(name)}"
						data-current-project="${this.esc(projectName)}">
						<span class="fh-field-outlined__label">${this.esc(__("Project"))}</span>
						<div class="fh-field-outlined__body">
							<span class="fh-field-outlined__value ${projectName ? "" : "is-empty"}">${this.esc(projectName)}</span>
							${projectName
								? `<button type="button" class="fh-field-outlined__clear" data-detail-clear-project="1" data-todo-name="${this.esc(name)}" title="${__("Clear")}">×</button>`
								: ""}
						</div>
					</div>
				</div>

				<div class="fh-detail__section">
					${isEditingDesc
						? `<div class="fh-detail__desc-editor">
							<textarea class="fh-detail__textarea" data-detail-desc-input="${this.esc(name)}">${this.esc(descValue || "")}</textarea>
							<div class="fh-detail__editor-actions">
								<button type="button" class="fh-detail__btn is-primary" data-detail-desc-save="${this.esc(name)}">${__("Save")}</button>
								<button type="button" class="fh-detail__btn" data-detail-desc-cancel="1">${__("Cancel")}</button>
							</div>
						</div>`
						: `<button type="button" class="fh-detail__line" data-detail-edit-desc="${this.esc(name)}">
							<span class="fh-detail__line-icon">≡</span>
							<span class="fh-detail__line-content">
								<span class="fh-detail__line-title">${hasDesc ? this.esc(__("Edit description")) : this.esc(__("Add description"))}</span>
								<span class="fh-detail__desc-text ${hasDesc ? "" : "fh-detail__desc-empty"}">${hasDesc ? descValue : this.esc(__("No description yet"))}</span>
							</span>
						</button>`
					}
				</div>

				<div class="fh-detail__section">
					<button type="button" class="fh-detail__line" data-detail-add-attachment="${this.esc(name)}">
						<span class="fh-detail__line-icon">+</span>
						<span class="fh-detail__line-content">
							<span class="fh-detail__line-title">${__("Add attachment")}</span>
							<span class="fh-detail__line-sub">${this.esc(__("Attach files directly to this ToDo"))}</span>
						</span>
					</button>
					<div class="fh-detail__attachment-list">${attachmentList}</div>
				</div>

				<div class="fh-detail__section">
					<button type="button" class="fh-detail__line" data-detail-edit-field="${this.esc(name)}">
						<span class="fh-detail__line-icon">+</span>
						<span class="fh-detail__line-content">
							<span class="fh-detail__line-title">${__("Add or edit field")}</span>
							${fieldSummary
								? `<span class="fh-detail__line-tags">${fieldSummary}</span>`
								: `<span class="fh-detail__line-sub">${this.esc(__("No extra fields yet"))}</span>`
							}
						</span>
					</button>
				</div>

				<div class="fh-detail__section">
					<div class="fh-detail__section-head">
						<div class="fh-detail__section-title">${__("Activity")}</div>
					</div>
					${isLoading && !activity.length ? `<div class="fh-detail__loading">${this.esc(__("Loading details…"))}</div>` : `<div class="fh-detail__activity">${activityHtml}</div>`}
				</div>
			</div>
			<div class="fh-detail__composer">
				<input type="text" class="fh-detail__composer-input" data-detail-comment-input="${this.esc(name)}" placeholder="${this.esc(__("Add comment"))}">
				<button type="button" class="fh-detail__composer-send" data-detail-comment-send="${this.esc(name)}">${__("Send")}</button>
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
			const normalized = String(value)
				.replace("T", " ")
				.replace("Z", "")
				.replace(/\.[0-9]+$/, "");

			const parsed = this._to_user_datetime(value);
			if (!parsed) return "";

			const date = typeof parsed.toDate === "function" ? parsed.toDate() : parsed;
			const relative = frappe.datetime && frappe.datetime.comment_when
				? frappe.datetime.comment_when(normalized, true)
				: this.esc(this._compact_relative_time(date));
			const full = typeof parsed.format === "function"
				? parsed.format("ddd, MMM D, HH:mm")
				: date.toLocaleString(undefined, {
					weekday: "short", month: "short", day: "numeric",
					hour: "2-digit", minute: "2-digit", hour12: false,
				});
			return `<span data-tip-name="${this.esc(__("Last updated"))}" data-tip-roles="${this.esc(full)}">${relative}</span>`;
		} catch {
			return "";
		}
	}

	_fmt_time_text(value) {
		if (!value) return "";
		try {
			const parsed = this._to_user_datetime(value);
			if (!parsed) return "";
			const date = typeof parsed.toDate === "function" ? parsed.toDate() : parsed;
			return this._compact_relative_time(date);
		} catch {
			return "";
		}
	}

	_to_user_datetime(value) {
		const normalized = String(value)
			.replace("T", " ")
			.replace("Z", "")
			.replace(/\.[0-9]+$/, "");

		if (frappe.datetime && frappe.datetime.convert_to_user_tz) {
			const userMoment = frappe.datetime.convert_to_user_tz(normalized, false);
			if (userMoment && typeof userMoment.isValid === "function" && userMoment.isValid()) {
				return userMoment;
			}
		}

		const fallback = new Date(value);
		return Number.isNaN(fallback.getTime()) ? null : fallback;
	}

	_compact_relative_time(date) {
		const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
		if (seconds < 45) return __("now");

		const minutes = Math.round(seconds / 60);
		if (minutes < 60) {
			return minutes === 1 ? __("1 min ago") : __("{0} mins ago", [minutes]);
		}

		const hours = Math.round(minutes / 60);
		if (hours < 24) {
			return hours === 1 ? __("1 hr ago") : __("{0} hrs ago", [hours]);
		}

		const days = Math.round(hours / 24);
		return days === 1 ? __("1 d ago") : __("{0} d ago", [days]);
	}

	esc(value) {
		return frappe.utils.escape_html(String(value ?? ""));
	}
};
