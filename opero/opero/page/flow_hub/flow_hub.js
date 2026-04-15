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

		this.page.set_primary_action(
			__("Refresh"),
			() => {
				this.refresh();
			},
			"refresh"
		);

		this.page.add_menu_item(__("Open Action Queue"), () => this.open_action_queue());
		frappe.breadcrumbs.add("Opero");

		this._ensure_styles();
		$(this.page.main).empty();
		this.$root = $("<div class='flow-hub'></div>").appendTo(this.page.main);
		this.render_loading();
		this.refresh();
	}

	_ensure_styles() {
		if (document.getElementById("flow-hub-styles")) {
			return;
		}

		const style = document.createElement("style");
		style.id = "flow-hub-styles";
		style.textContent = `
			.flow-hub {
				--flow-bg: #f8fafc;
				--flow-card: #ffffff;
				--flow-text: #0f172a;
				--flow-muted: #64748b;
				--flow-border: rgba(15, 23, 42, 0.12);
				--flow-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
				font-family: "Space Grotesk", "Avenir Next", "Trebuchet MS", sans-serif;
				padding: 1rem;
				background: radial-gradient(circle at 10% 10%, #e0f2fe 0%, #f8fafc 45%, #f0fdf4 100%);
				min-height: calc(100vh - 120px);
			}

			.flow-hub__hero {
				position: relative;
				padding: 0.8rem 1rem;
				border-radius: 14px;
				background: linear-gradient(132deg, #0f766e 0%, #0284c7 48%, #f59e0b 100%);
				color: #f8fafc;
				overflow: hidden;
				box-shadow: 0 12px 24px rgba(2, 8, 23, 0.2);
				display: grid;
				gap: 0.55rem;
			}

			.flow-hub__hero::after {
				content: "";
				position: absolute;
				right: -52px;
				top: -55px;
				width: 140px;
				height: 140px;
				background: radial-gradient(circle, rgba(255, 255, 255, 0.34) 0%, rgba(255, 255, 255, 0) 72%);
				pointer-events: none;
			}

			.flow-hub__hero-top {
				display: flex;
				align-items: center;
				justify-content: space-between;
				gap: 0.7rem;
			}

			.flow-hub__subtitle {
				margin: 0;
				font-size: 0.9rem;
				opacity: 0.95;
			}

			.flow-hub__hero-meta {
				display: flex;
				flex-wrap: wrap;
				gap: 0.45rem;
				font-size: 0.78rem;
				opacity: 0.95;
			}

			.flow-hub__hero-pill {
				padding: 0.24rem 0.48rem;
				border-radius: 999px;
				background: rgba(255, 255, 255, 0.18);
				backdrop-filter: blur(2px);
			}

			.flow-hub__button {
				border: 1px solid rgba(255, 255, 255, 0.5);
				background: rgba(255, 255, 255, 0.16);
				color: #fff;
				padding: 0.36rem 0.7rem;
				border-radius: 9px;
				font-size: 0.8rem;
				cursor: pointer;
				transition: transform 160ms ease, background 160ms ease;
				white-space: nowrap;
			}

			.flow-hub__button:hover {
				background: rgba(255, 255, 255, 0.28);
				transform: translateY(-1px);
			}

			.flow-hub__cards {
				display: grid;
				grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
				gap: 0.65rem;
				margin-top: 0.65rem;
			}

			.flow-hub__card {
				position: relative;
				border: 1px solid var(--flow-border);
				border-radius: 12px;
				background: linear-gradient(160deg, var(--flow-card) 0%, #f8fbff 100%);
				padding: 0.65rem;
				text-align: left;
				box-shadow: var(--flow-shadow);
				cursor: pointer;
				transition: transform 180ms ease, border-color 180ms ease;
				animation: flow-hub-rise 350ms ease both;
			}

			.flow-hub__card::before {
				content: "";
				position: absolute;
				left: 0;
				top: 0;
				width: 100%;
				height: 3px;
				background: var(--card-accent, #2563eb);
				border-radius: 12px 12px 0 0;
			}

			.flow-hub__card:hover {
				transform: translateY(-2px);
				border-color: rgba(37, 99, 235, 0.28);
			}

			.flow-hub__card-label {
				font-size: 0.76rem;
				color: var(--flow-muted);
				margin-bottom: 0.35rem;
			}

			.flow-hub__card-value {
				font-size: 1.3rem;
				font-weight: 700;
				letter-spacing: -0.02em;
				color: var(--flow-text);
			}

			.flow-hub__layout {
				display: grid;
				grid-template-columns: 1.2fr 1fr;
				gap: 0.65rem;
				margin-top: 0.7rem;
			}

			.flow-hub__panel {
				border: 1px solid var(--flow-border);
				border-radius: 14px;
				padding: 0.72rem;
				background: linear-gradient(170deg, #ffffff 0%, #f8fafc 100%);
				box-shadow: var(--flow-shadow);
			}

			.flow-hub__panel-title {
				margin: 0;
				font-size: 1rem;
				color: #0f172a;
			}

			.flow-hub__panel-subtitle {
				margin: 0.2rem 0 0.6rem;
				font-size: 0.77rem;
				color: var(--flow-muted);
			}

			.flow-hub__list {
				display: grid;
				gap: 0.6rem;
			}

			.flow-hub__item {
				border: 1px solid rgba(15, 23, 42, 0.08);
				border-radius: 12px;
				padding: 0.55rem 0.65rem;
				background: #ffffff;
				cursor: pointer;
				transition: border-color 160ms ease, transform 160ms ease;
			}

			.flow-hub__item:hover {
				border-color: rgba(2, 132, 199, 0.35);
				transform: translateY(-1px);
			}

			.flow-hub__item-title {
				font-size: 0.84rem;
				font-weight: 600;
				color: #0f172a;
				line-height: 1.35;
			}

			.flow-hub__item-meta {
				display: flex;
				align-items: center;
				gap: 0.45rem;
				flex-wrap: wrap;
				margin-top: 0.35rem;
				font-size: 0.72rem;
				color: #475569;
			}

			.flow-hub__status {
				padding: 0.17rem 0.44rem;
				border-radius: 999px;
				font-size: 0.71rem;
				font-weight: 600;
				text-transform: uppercase;
				letter-spacing: 0.03em;
			}

			.flow-hub__status.is-open {
				background: #eff6ff;
				color: #1d4ed8;
			}

			.flow-hub__status.is-in-progress {
				background: #eff6ff;
				color: #1e3a8a;
			}

			.flow-hub__status.is-closed {
				background: #ecfdf5;
				color: #047857;
			}

			.flow-hub__status.is-cancelled {
				background: #fef2f2;
				color: #b91c1c;
			}

			.flow-hub__priority {
				padding: 0.16rem 0.4rem;
				border-radius: 999px;
				background: #fff7ed;
				color: #b45309;
			}

			.flow-hub__empty {
				padding: 0.72rem;
				border-radius: 12px;
				background: #f8fafc;
				border: 1px dashed rgba(15, 23, 42, 0.2);
				font-size: 0.8rem;
				color: #64748b;
			}

			.flow-hub__skeleton {
				border-radius: 14px;
				height: 78px;
				background: linear-gradient(90deg, #e2e8f0 0%, #f8fafc 50%, #e2e8f0 100%);
				background-size: 200% 100%;
				animation: flow-hub-shimmer 1.2s linear infinite;
			}

			.flow-hub__error {
				padding: 0.8rem;
				border: 1px solid #fecaca;
				background: #fff1f2;
				color: #9f1239;
				border-radius: 12px;
			}

			@keyframes flow-hub-shimmer {
				0% { background-position: 200% 0; }
				100% { background-position: -200% 0; }
			}

			@keyframes flow-hub-rise {
				0% { opacity: 0; transform: translateY(5px); }
				100% { opacity: 1; transform: translateY(0); }
			}

			@media (max-width: 980px) {
				.flow-hub__layout {
					grid-template-columns: 1fr;
				}
			}

			@media (max-width: 640px) {
				.flow-hub {
					padding: 0.65rem;
				}

				.flow-hub__hero {
					padding: 0.7rem;
				}

				.flow-hub__cards {
					grid-template-columns: repeat(2, minmax(0, 1fr));
				}

				.flow-hub__hero-top {
					flex-direction: column;
					align-items: flex-start;
				}
			}
		`;
		document.head.appendChild(style);
	}

	render_loading() {
		this.$root.html(`
			<section class="flow-hub__hero">
				<p class="flow-hub__subtitle">Loading your current ToDo flow...</p>
			</section>
			<section class="flow-hub__cards">
				<div class="flow-hub__skeleton"></div>
				<div class="flow-hub__skeleton"></div>
				<div class="flow-hub__skeleton"></div>
				<div class="flow-hub__skeleton"></div>
			</section>
		`);
	}

	render_error() {
		this.$root.html(`
			<div class="flow-hub__error">
				${this.escape_html(__("Flow Hub could not load right now. Please refresh once."))}
			</div>
		`);
	}

	refresh() {
		if (this.loading) {
			return;
		}

		this.loading = true;
		this.render_loading();

		frappe.call({
			method: "opero.todo_dashboard.get_flow_hub_snapshot",
			callback: (response) => {
				this.loading = false;
				this.snapshot = response.message || {};
				this.render();
			},
			error: () => {
				this.loading = false;
				this.render_error();
			},
		});
	}

	render() {
		const snapshot = this.snapshot || {};
		const cards = snapshot.cards || [];
		const upcoming = snapshot.upcoming || [];
		const recent = snapshot.recently_finished || [];
		const activeTotal = Number.parseInt(snapshot.active_total || 0, 10) || 0;
		const updatedAt = snapshot.updated_at || "";

		this.$root.html(`
			<section class="flow-hub__hero">
				<div class="flow-hub__hero-top">
					<p class="flow-hub__subtitle">Momentum, risk, and completion flow in one glance.</p>
					<button type="button" class="flow-hub__button" data-action="open-action-queue">${this.escape_html(
						__("Open Action Queue")
					)}</button>
				</div>
				<div class="flow-hub__hero-meta">
					<span class="flow-hub__hero-pill">${this.escape_html(__("Active: {0}", [activeTotal]))}</span>
					<span class="flow-hub__hero-pill">${this.escape_html(this.format_datetime(updatedAt))}</span>
				</div>
			</section>
			<section class="flow-hub__cards">
				${this.render_cards(cards)}
			</section>
			<section class="flow-hub__layout">
				<article class="flow-hub__panel">
					<h2 class="flow-hub__panel-title">${this.escape_html(__("Upcoming Flow"))}</h2>
					<p class="flow-hub__panel-subtitle">${this.escape_html(
						__("Prioritized by due date and recency. Click a card to open the ToDo.")
					)}</p>
					<div class="flow-hub__list">
						${this.render_todo_rows(upcoming, "upcoming")}
					</div>
				</article>
				<article class="flow-hub__panel">
					<h2 class="flow-hub__panel-title">${this.escape_html(__("Recently Finished"))}</h2>
					<p class="flow-hub__panel-subtitle">${this.escape_html(
						__("Closed and cancelled items in your scope.")
					)}</p>
					<div class="flow-hub__list">
						${this.render_todo_rows(recent, "recent")}
					</div>
				</article>
			</section>
		`);

		this.bind_events(cards, upcoming, recent);
	}

	render_cards(cards) {
		if (!cards.length) {
			return `<div class="flow-hub__empty">${this.escape_html(__("No metrics available yet."))}</div>`;
		}

		return cards
			.map((card, index) => {
				const accent = this.escape_html(card.accent || "#2563eb");
				return `
					<button type="button" class="flow-hub__card" data-card-index="${index}" style="--card-accent:${accent}">
						<div class="flow-hub__card-label">${this.escape_html(card.label || "")}</div>
						<div class="flow-hub__card-value">${this.escape_html(this.format_metric(card))}</div>
					</button>
				`;
			})
			.join("");
	}

	render_todo_rows(rows, section) {
		if (!rows.length) {
			return `<div class="flow-hub__empty">${this.escape_html(__("Nothing to show."))}</div>`;
		}

		return rows
			.map((row, index) => {
				const statusClass = this.get_status_class(row.status);
				const priority = row.is_high_priority
					? `<span class="flow-hub__priority">${this.escape_html(row.priority || __("High"))}</span>`
					: "";

				return `
					<button type="button" class="flow-hub__item" data-section="${section}" data-item-index="${index}">
						<div class="flow-hub__item-title">${this.escape_html(row.title || row.name || "")}</div>
						<div class="flow-hub__item-meta">
							<span class="flow-hub__status ${statusClass}">${this.escape_html(row.status || "")}</span>
							${priority}
							<span>${this.escape_html(row.due_label || __("No due date"))}</span>
						</div>
					</button>
				`;
			})
			.join("");
	}

	bind_events(cards, upcoming, recent) {
		this.$root.find("[data-action='open-action-queue']").on("click", () => this.open_action_queue());

		this.$root.find("[data-card-index]").each((_, element) => {
			const index = Number.parseInt($(element).attr("data-card-index"), 10) || 0;
			$(element).on("click", () => {
				this.navigate_to_card(cards[index]);
			});
		});

		this.$root.find("[data-section][data-item-index]").each((_, element) => {
			const section = $(element).attr("data-section");
			const index = Number.parseInt($(element).attr("data-item-index"), 10) || 0;
			const source = section === "recent" ? recent : upcoming;
			const row = source[index];
			$(element).on("click", () => {
				if (row && row.name) {
					frappe.set_route("Form", "ToDo", row.name);
				}
			});
		});
	}

	navigate_to_card(card) {
		if (!card || !Array.isArray(card.route) || !card.route.length) {
			return;
		}

		frappe.route_options = card.route_options || {};
		frappe.set_route(...card.route);
	}

	open_action_queue() {
		frappe.route_options = { status: ["Open", "In Progress"] };
		frappe.set_route("query-report", "ToDo Action Queue");
	}

	format_metric(card) {
		const value = card ? card.value : 0;
		const fieldtype = (card && card.fieldtype) || "Int";

		if (fieldtype === "Percent") {
			return `${Number(value || 0).toFixed(1)}%`;
		}

		if (fieldtype === "Float") {
			return `${Number(value || 0).toFixed(2)}`;
		}

		return `${Number.parseInt(value || 0, 10) || 0}`;
	}

	format_datetime(value) {
		if (!value) {
			return __("Updated just now");
		}

		try {
			const userFormatted = frappe.datetime.str_to_user(value);
			return __("Updated: {0}", [userFormatted]);
		} catch (error) {
			return __("Updated just now");
		}
	}

	get_status_class(status) {
		const key = (status || "")
			.toLowerCase()
			.trim()
			.replace(/[^a-z0-9]+/g, "-")
			.replace(/(^-|-$)/g, "");
		return `is-${key || "open"}`;
	}

	escape_html(value) {
		return frappe.utils.escape_html(String(value || ""));
	}
};
