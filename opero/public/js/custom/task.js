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

frappe.ui.form.on("Task", {
	refresh(frm) {
		opero.task_allocation.load(frm);
	},
});

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
			return `<tr><td>${esc(employee_name)}</td>${cells}<td class="text-right"><strong>${fmt(
				total
			)}</strong></td></tr>`;
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
	)}</th></tr></thead>
				<tbody>${
					body ||
					`<tr><td colspan="${grid.months.length + 2}" class="text-muted">${__(
						"No allocations yet."
					)}</td></tr>`
				}</tbody>
				<tfoot><tr><td><strong>${__("Total")}</strong></td>${totals}<td class="text-right"><strong>${fmt(
		grand
	)}</strong></td></tr></tfoot>
			</table>
			${
				grid.can_create
					? `<button class="btn btn-xs btn-default opero-new-allocation">${__(
							"New allocation"
					  )}</button>`
					: ""
			}
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
