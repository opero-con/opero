frappe.ui.form.on("Task Allocation", {
	onload(frm) {
		if (!frm.is_new()) return;
		const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
		const months = frm.get_docfield("month").options.split("\n").filter(Boolean);
		if (!frm.doc.month) frm.set_value("month", months[today.getMonth()]);
		if (!frm.doc.year) frm.set_value("year", String(today.getFullYear()));
	},
	refresh: show_ribbon,
	task: show_ribbon,
	employee: show_ribbon,
	month: show_ribbon,
	year: show_ribbon,
	hours: show_ribbon,
});

function set_ribbon(frm, lines, color) {
	let ribbon = frm.layout.wrapper.find(".opero-allocation-ribbon");
	if (!ribbon.length) {
		ribbon = $('<div class="opero-allocation-ribbon form-message"></div>').prependTo(
			frm.layout.wrapper
		);
	}
	ribbon.removeClass("green orange blue red").addClass(color).html(lines.join("<br>"));
	ribbon.toggle(lines.length > 0);
}

function show_ribbon(frm) {
	const { task, employee, month, year, docstatus } = frm.doc;
	const request = (frm.allocation_ribbon_request = (frm.allocation_ribbon_request || 0) + 1);
	if (!employee || !month || !/^\d{4}$/.test(year || "") || docstatus === 2) {
		set_ribbon(frm, [], "blue");
		return;
	}
	frappe
		.xcall("opero.api.task_allocation.get_capacity", {
			employee,
			month,
			year,
			task,
			name: frm.is_new() ? null : frm.doc.name,
		})
		.then((capacity) => {
			if (request !== frm.allocation_ribbon_request) return;
			if (task && !capacity.budget) {
				const esc = frappe.utils.escape_html;
				const link = frappe.utils.get_form_link(
					"Task",
					task,
					true,
					esc(capacity.task_subject || task)
				);
				const message = __("No Hours Budget for {0} on task {1}.", [
					frappe.bold(esc(frm.doc.personnel_name || employee)),
					link,
				]);
				set_ribbon(frm, [message], "red");
				return;
			}
			const { lines, color } = describe_capacity(frm.doc.hours || 0, capacity);
			set_ribbon(frm, lines, color);
		});
}

function describe_capacity(hours, capacity) {
	const lines = [];
	const warnings = [];
	if (capacity.budget) {
		const committed = flt(capacity.task_allocated + hours, 2);
		const left = flt(capacity.budget.hours - committed, 2);
		if (left < 0) {
			warnings.push(
				__("Budget: {0}h overrun ({1}h of {2}h).", [
					-left,
					committed,
					capacity.budget.hours,
				])
			);
		} else {
			lines.push(__("Budget: {0}h left of {1}h.", [left, capacity.budget.hours]));
		}
	}
	if (capacity.same_task.length) {
		const earlier = flt(
			capacity.same_task.reduce((sum, row) => sum + row.hours, 0),
			2
		);
		warnings.push(
			__("Already {0}h on this task this month; {1}h with this.", [
				earlier,
				flt(earlier + hours, 2),
			])
		);
	}
	const total = flt(capacity.allocated + hours, 2);
	if (capacity.available === null) {
		lines.push(__("Month: {0}h allocated, availability unknown.", [total]));
	} else {
		const free = flt(capacity.available - total, 2);
		if (free < 0) {
			warnings.push(
				__("Month: {0}h over capacity ({1}h of {2}h).", [-free, total, capacity.available])
			);
		} else {
			lines.push(__("Month: {0}h free of {1}h.", [free, capacity.available]));
		}
	}
	const color = warnings.length ? "orange" : capacity.available === null ? "blue" : "green";
	return { lines: [...warnings, ...lines], color };
}
