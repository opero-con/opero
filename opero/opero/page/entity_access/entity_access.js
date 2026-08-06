// Entity Access — who may see which entity's records.
//
// Company User Permissions decide this, and their one counter-intuitive rule is
// that a user with NO permission sees everything. This page makes that state
// visible instead of leaving it implied by an empty checkbox row.

frappe.pages["entity-access"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Entity Access"),
		single_column: true,
	});

	const view = new EntityAccess(page);
	view.load();
};

class EntityAccess {
	constructor(page) {
		this.page = page;
		this.query = "";
		this.matrix = { entities: [], users: [] };

		this._inject_styles();
		this.$body = $('<div class="ea"></div>').appendTo(page.main);

		this.page.add_field({
			fieldname: "search",
			fieldtype: "Data",
			label: __("Search user"),
			change: () => {
				this.query = (this.page.fields_dict.search.get_value() || "").toLowerCase();
				this.render();
			},
		});

		this.page.set_primary_action(__("Reload"), () => this.load());
	}

	async load() {
		frappe.dom.freeze(__("Loading entity access…"));
		try {
			this.matrix = await frappe.xcall("opero.api.entity_access.get_access_matrix");
		} finally {
			frappe.dom.unfreeze();
		}
		this.render();
	}

	visible_users() {
		if (!this.query) return this.matrix.users;
		return this.matrix.users.filter(
			(u) =>
				u.full_name.toLowerCase().includes(this.query) ||
				u.user.toLowerCase().includes(this.query)
		);
	}

	render() {
		const entities = this.matrix.entities || [];
		const users = this.visible_users();

		if (!entities.length) {
			this.$body.html(
				`<div class="ea-empty">${__("No companies are set up on this site yet.")}</div>`
			);
			return;
		}

		const head = entities
			.map(
				(e) =>
					`<th class="ea-entity" title="${frappe.utils.escape_html(e.name)}">
						${frappe.utils.escape_html(e.label)}
					</th>`
			)
			.join("");

		const rows = users.map((u) => this.render_row(u, entities)).join("");

		this.$body.html(`
			<p class="ea-hint">${__(
				"A user with no entity ticked sees every entity. Tick one or more to restrict them — remember to include their own."
			)}</p>
			<div class="ea-scroll">
				<table class="ea-table">
					<thead>
						<tr>
							<th>${__("User")}</th>
							<th>${__("Employer")}</th>
							${head}
							<th></th>
						</tr>
					</thead>
					<tbody>${rows || `<tr><td colspan="${entities.length + 3}" class="ea-empty">${__(
						"No users match."
					)}</td></tr>`}</tbody>
				</table>
			</div>
		`);

		this.$body.find("[data-toggle-entity]").on("change", (event) => {
			const $box = $(event.currentTarget);
			this.save($box.attr("data-user"));
		});
	}

	label_for(company) {
		const entity = (this.matrix.entities || []).find((e) => e.name === company);
		return (entity && entity.label) || company;
	}

	render_row(user, entities) {
		const cells = entities
			.map((entity) => {
				const checked = user.allowed.includes(entity.name) ? "checked" : "";
				return `<td class="ea-cell">
					<input type="checkbox" data-toggle-entity
						data-user="${frappe.utils.escape_html(user.user)}"
						data-entity="${frappe.utils.escape_html(entity.name)}" ${checked}>
				</td>`;
			})
			.join("");

		const unrestricted = user.allowed.length
			? ""
			: `<span class="ea-badge">${__("all entities")}</span>`;

		return `<tr data-row-user="${frappe.utils.escape_html(user.user)}">
			<td>
				<div class="ea-name">${frappe.utils.escape_html(user.full_name)}</div>
				<div class="ea-sub">${frappe.utils.escape_html(user.user)}</div>
			</td>
			<td class="ea-sub">${frappe.utils.escape_html(
				user.employer ? this.label_for(user.employer) : "—"
			)}</td>
			${cells}
			<td>${unrestricted}</td>
		</tr>`;
	}

	async save(user) {
		// Matched in JS rather than through a selector: usernames are email
		// addresses, which need escaping the moment they go into one.
		const companies = this.$body
			.find("[data-toggle-entity]:checked")
			.filter((_i, el) => el.getAttribute("data-user") === user)
			.map((_i, el) => el.getAttribute("data-entity"))
			.get();

		try {
			const result = await frappe.xcall("opero.api.entity_access.set_access", {
				user,
				companies,
			});
			const record = this.matrix.users.find((u) => u.user === user);
			if (record) record.allowed = result.allowed;
			this.render();
			frappe.show_alert({
				message: result.allowed.length
					? __("{0} restricted to {1}", [
							user,
							result.allowed.map((c) => this.label_for(c)).join(", "),
					  ])
					: __("{0} can now see every entity", [user]),
				indicator: "green",
			});
		} catch (error) {
			this.load();
		}
	}

	_inject_styles() {
		if (document.getElementById("ea-styles")) return;
		$(`<style id="ea-styles">
			.ea { -webkit-font-smoothing: antialiased; }
			.ea-hint {
				font-size: var(--text-sm);
				color: var(--text-muted);
				margin-bottom: 12px;
				max-width: 60ch;
			}
			.ea-scroll { overflow-x: auto; }
			.ea-table { width: 100%; border-collapse: collapse; }
			.ea-table th {
				text-align: left;
				font-size: var(--text-sm);
				font-weight: var(--weight-semibold);
				color: var(--text-muted);
				padding: 6px 12px 6px 0;
				border-bottom: 1px solid var(--border-color);
				white-space: nowrap;
			}
			.ea-table td {
				padding: 8px 12px 8px 0;
				border-bottom: 1px solid var(--border-color);
				font-size: var(--text-base);
				vertical-align: middle;
			}
			.ea-table th.ea-entity, .ea-table td.ea-cell { text-align: center; padding-right: 0; }
			.ea-name { color: var(--text-color); }
			.ea-sub { font-size: var(--text-sm); color: var(--text-muted); }
			.ea-badge {
				font-size: var(--text-xs);
				color: var(--text-muted);
				background: var(--bg-color);
				border-radius: 8px;
				padding: 2px 8px;
				white-space: nowrap;
			}
			.ea-empty {
				padding: 24px 0;
				font-size: var(--text-base);
				color: var(--text-muted);
				text-align: center;
			}
		</style>`).appendTo(document.head);
	}
}
