frappe.ui.form.on("Task Allocation", {
	onload(frm) {
		if (!frm.is_new()) return;
		const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
		const months = frm.get_docfield("month").options.split("\n").filter(Boolean);
		if (!frm.doc.month) frm.set_value("month", months[today.getMonth()]);
		if (!frm.doc.year) frm.set_value("year", String(today.getFullYear()));
	},
	refresh(frm) {
		frm.allocation_capacity = null;
		show_allocation_summary(frm);
	},
	task: show_allocation_summary,
	employee: show_allocation_summary,
	month: show_allocation_summary,
	year: show_allocation_summary,
	personnel_name(frm) {
		if (frm.doc.docstatus === 0 && frm.allocation_capacity) {
			set_allocation_summary(frm, capacity_table(frm.doc, frm.allocation_capacity));
		}
	},
	hours(frm) {
		if (frm.doc.docstatus === 0 && frm.allocation_capacity) {
			set_allocation_summary(frm, capacity_table(frm.doc, frm.allocation_capacity));
		} else {
			show_allocation_summary(frm);
		}
	},
});

function set_allocation_summary(frm, html) {
	const title = __("Allocations - {0}", [frm.doc.personnel_name || frm.doc.employee || ""]);
	let content = frm.dashboard.parent.find(".opero-allocation-summary-content");
	if (!content.length && html) {
		const body = frm.dashboard.add_section(
			'<div class="opero-allocation-summary-content"></div>',
			`<span class="opero-allocation-heading">${frappe.utils.escape_html(title)}</span>`,
			"custom opero-allocation-summary"
		);
		content = body.find(".opero-allocation-summary-content");
	}
	if (!content.length) return;
	content.html(html);
	const section = content.closest(".form-dashboard-section");
	section.find(".opero-allocation-heading").text(title);
	section.toggle(!!html);
	if (html) frm.dashboard.show();
}

function show_allocation_summary(frm) {
	const { task, employee, month, year, docstatus } = frm.doc;
	const request = (frm.allocation_summary_request = (frm.allocation_summary_request || 0) + 1);
	frm.allocation_capacity = null;
	if (!employee || !month || !/^\d{4}$/.test(year || "") || docstatus !== 0) {
		set_allocation_summary(frm, "");
		return;
	}
	return frappe
		.xcall("opero.api.task_allocation.get_capacity", {
			employee,
			month,
			year,
			task,
			name: frm.is_new() ? null : frm.doc.name,
		})
		.then((capacity) => {
			if (request !== frm.allocation_summary_request) return;
			frm.allocation_capacity = capacity;
			set_allocation_summary(frm, capacity_table(frm.doc, capacity));
		})
		.catch(() => {
			if (request !== frm.allocation_summary_request) return;
			set_allocation_summary(
				frm,
				__("Could not load allocation totals. Refresh to try again.")
			);
		});
}

function capacity_table(doc, capacity) {
	const esc = frappe.utils.escape_html;
	const hours = flt(doc.hours || 0, 2);
	const month = `${doc.month} ${doc.year}`;
	const rows = [];
	if (doc.task) {
		rows.push({
			scope: capacity.task_subject || doc.task,
			limit: capacity.budget ? capacity.budget.hours : null,
			other: capacity.task_allocated,
		});
	}
	rows.push({
		scope: __("All - {0}", [month]),
		limit: capacity.available,
		other: capacity.allocated,
	});
	const missing_budget = doc.task && !capacity.budget;
	const note = missing_budget
		? `<p class="text-danger">${__("No Hours Budget for {0} on task {1}.", [
				esc(doc.personnel_name || doc.employee),
				frappe.utils.get_form_link(
					"Task",
					doc.task,
					true,
					esc(capacity.task_subject || doc.task)
				),
		  ])}</p>`
		: "";
	return `${note}<div class="table-responsive"><table class="table table-bordered small" style="table-layout: fixed">
		<thead><tr>
			<th style="width: 35%">${esc(__("Task"))}</th>
			${["Budget / Capacity", "Allocations", "Total", "Remaining"]
				.map((label) => `<th class="text-right">${esc(__(label))}</th>`)
				.join("")}
		</tr></thead><tbody>${rows
			.map((row) => {
				const total = flt(row.other + hours, 2);
				const remaining = row.limit === null ? null : flt(row.limit - total, 2);
				const balance =
					remaining === null
						? "—"
						: remaining < 0
						? esc(__("{0}h over", [-remaining]))
						: `${remaining}h`;
				return `<tr><td>${esc(row.scope)}</td>
			<td class="text-right">${row.limit === null ? "—" : `${flt(row.limit, 2)}h`}</td>
			<td class="text-right">${flt(row.other, 2)}h</td>
			<td class="text-right">${total}h</td>
			<td class="text-right${remaining < 0 ? " text-danger" : ""}">${balance}</td></tr>`;
			})
			.join("")}</tbody></table></div>`;
}
