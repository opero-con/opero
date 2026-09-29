// Opero: client scripts for Task

frappe.provide("opero.task_allocation");

opero.task_allocation.MONTHS = [
	"Jan",
	"Feb",
	"Mar",
	"Apr",
	"May",
	"Jun",
	"Jul",
	"Aug",
	"Sep",
	"Oct",
	"Nov",
	"Dec",
];

opero.task_allocation.OVERRUN_STYLE = "color: var(--orange-600)";

frappe.ui.form.on("Task", {
	refresh(frm) {
		opero.task_allocation.setup_budget_table(frm);
		opero.task_allocation.load(frm);
	},
});

frappe.ui.form.on("Task Time Allocation", {
	new_allocation(frm, cdt, cdn) {
		opero.task_allocation.new_for_budget_row(frm, locals[cdt][cdn]);
	},
	days(frm, cdt, cdn) {
		opero.task_allocation.sync_budget(
			cdt,
			cdn,
			"days",
			"hours",
			(days, standard) => days * standard
		);
	},
	hours(frm, cdt, cdn) {
		opero.task_allocation.sync_budget(
			cdt,
			cdn,
			"hours",
			"days",
			(hours, standard) => hours / standard
		);
	},
});

opero.task_allocation.sync_budget = function (cdt, cdn, source, target, convert) {
	opero.task_allocation.standard_hours ||= frappe.db.get_single_value(
		"HR Settings",
		"standard_working_hours"
	);
	opero.task_allocation.standard_hours.then((standard) => {
		const row = locals[cdt][cdn];
		if (!flt(standard) || !row) return;
		const value = flt(convert(flt(row[source]), flt(standard)), 2);
		if (flt(row[target]) !== value) frappe.model.set_value(cdt, cdn, target, value);
	});
};

opero.task_allocation.row_button = function (css_class, title, icon) {
	return (value, df, options, doc) =>
		doc && doc.name
			? `<button class="btn btn-xs btn-default ${css_class}" data-row="${frappe.utils.escape_html(
					doc.name
			  )}" title="${title}">${frappe.utils.icon(icon, "xs")}</button>`
			: "";
};

opero.task_allocation.setup_budget_table = function (frm) {
	const field = frm.get_field("custom_time_allocation");
	if (!field) return;
	// Rows keep their own docfield copies, so formatters go through the grid.
	field.grid.update_docfield_property("overrun", "formatter", (value) =>
		flt(value)
			? `<span style="${opero.task_allocation.OVERRUN_STYLE}">${format_number(
					value,
					null,
					2
			  )}</span>`
			: ""
	);
	const button = opero.task_allocation.row_button;
	field.grid.update_docfield_property(
		"new_allocation",
		"formatter",
		button("opero-row-allocate", __("New allocation"), "add")
	);
	const find_row = (event) =>
		(frm.doc.custom_time_allocation || []).find(
			(budget) => budget.name === event.currentTarget.dataset.row
		);
	field.grid.wrapper.off("click.opero").on("click.opero", ".opero-row-allocate", (event) => {
		event.preventDefault();
		event.stopPropagation();
		opero.task_allocation.new_for_budget_row(frm, find_row(event));
	});
	field.grid.refresh();
};

opero.task_allocation.is_budget_row_ready = function (frm, row) {
	if (frm.is_new() || frm.is_dirty()) {
		frappe.msgprint(__("Save the task before allocating hours."));
		return false;
	}
	if (!row || !row.personnel) {
		frappe.msgprint(__("Choose the personnel on this budget row first."));
		return false;
	}
	return true;
};

opero.task_allocation.new_for_budget_row = function (frm, row) {
	if (!opero.task_allocation.is_budget_row_ready(frm, row)) return;
	frappe.new_doc("Task Allocation", { task: frm.doc.name, employee: row.personnel });
};

opero.task_allocation.load = function (frm) {
	const field = frm.get_field("custom_allocation_grid");
	if (!field) return;
	if (frm.is_new()) {
		field.$wrapper.html(`<p class="text-muted">${__("Save the task to allocate hours.")}</p>`);
		return;
	}
	frappe
		.xcall("opero.api.task_allocation.get_allocation_grid", { task: frm.doc.name })
		.then((grid) => opero.task_allocation.render(frm, grid));
};

opero.task_allocation.render = function (frm, grid) {
	const field = frm.get_field("custom_allocation_grid");
	const lookup = (rows) => {
		const map = {};
		rows.forEach(([employee, month, hours]) => (map[`${employee}|${month}`] = hours));
		return map;
	};
	const allocated = lookup(grid.allocated);
	const used = lookup(grid.used);
	const fmt = (n) => format_number(n || 0, null, 2).replace(/\.00$/, "");
	const label = (month) => moment(month).format("MMM YY");
	const esc = frappe.utils.escape_html;

	const header = grid.months.map((m) => `<th class="text-right">${label(m)}</th>`).join("");
	const body = grid.employees
		.map(({ employee, employee_name }) => {
			let total = 0;
			const cells = grid.months
				.map((month) => {
					const key = `${employee}|${month}`;
					const hours = allocated[key] || 0;
					const spent = used[key] || 0;
					total += hours;
					const value = grid.can_create
						? `<a href="#" class="opero-new-allocation" data-employee="${esc(
								employee
						  )}"
							data-month="${month}" title="${__("New allocation")}">${fmt(hours)}</a>`
						: `<div>${fmt(hours)}</div>`;
					const note = spent
						? `<div class="small ${spent > hours ? "text-danger" : "text-muted"}">${__(
								"used"
						  )} ${fmt(spent)}</div>`
						: "";
					return `<td class="text-right">${value}${note}</td>`;
				})
				.join("");
			const budget = opero.task_allocation.budget_cell(grid.budgets[employee], total, fmt);
			return `<tr><td>${esc(employee_name)}</td>${cells}<td class="text-right"><strong>${fmt(
				total
			)}</strong></td>${budget}</tr>`;
		})
		.join("");
	const totals = grid.months
		.map((month) => {
			const sum = grid.employees.reduce(
				(s, e) => s + (allocated[`${e.employee}|${month}`] || 0),
				0
			);
			return `<td class="text-right"><strong>${fmt(sum)}</strong></td>`;
		})
		.join("");
	const grand = grid.allocated.reduce((s, row) => s + row[2], 0);

	field.$wrapper.html(`
		<div class="opero-allocation-grid" style="overflow-x:auto">
			<table class="table table-bordered table-sm">
				<thead><tr><th>${__("Employee")}</th>${header}<th class="text-right">${__(
		"Total"
	)}</th><th class="text-right">${__("Budget")}</th></tr></thead>
				<tbody>${
					body ||
					`<tr><td colspan="${grid.months.length + 3}" class="text-muted">${__(
						"No allocations yet."
					)}</td></tr>`
				}</tbody>
				<tfoot><tr><td><strong>${__("Total")}</strong></td>${totals}<td class="text-right"><strong>${fmt(
		grand
	)}</strong></td><td class="text-right"><strong>${fmt(
		Object.values(grid.budgets).reduce((sum, budget) => sum + budget.hours, 0)
	)}</strong></td></tr></tfoot>
			</table>
			${
				grid.months.length
					? ""
					: `<p class="text-muted small">${__(
							"Set the task's From and To dates to show months."
					  )}</p>`
			}
		</div>`);

	field.$wrapper.find(".opero-new-allocation").on("click", function (event) {
		event.preventDefault();
		const values = { task: frm.doc.name };
		if (this.dataset.employee) values.employee = this.dataset.employee;
		if (this.dataset.month) {
			const [year, month] = this.dataset.month.split("-");
			values.year = year;
			values.month = opero.task_allocation.MONTHS[Number(month) - 1];
		}
		frappe.new_doc("Task Allocation", values);
	});
};

opero.task_allocation.budget_cell = function (budget, allocated, fmt) {
	if (!budget) return `<td class="text-right text-muted">${__("none")}</td>`;
	const note = budget.overrun
		? `<div class="small" style="${opero.task_allocation.OVERRUN_STYLE}">${__(
				"overrun"
		  )} ${fmt(budget.overrun)}</div>`
		: `<div class="small text-muted">${__("left")} ${fmt(budget.hours - allocated)}</div>`;
	return `<td class="text-right"><strong>${fmt(budget.hours)}</strong>${note}</td>`;
};
