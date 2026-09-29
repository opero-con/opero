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
	ribbon.removeClass("green orange blue").addClass(color).html(lines.join("<br>"));
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
			const { lines, color } = describe_capacity(frm, capacity);
			set_ribbon(frm, lines, color);
		});
}

function describe_capacity(frm, { available, allocated, same_task }) {
	const who = frm.doc.personnel_name || frm.doc.employee;
	const period = `${frm.doc.month} ${frm.doc.year}`;
	const hours = frm.doc.hours || 0;
	const lines = [];
	let color = "green";

	if (same_task.length) {
		const earlier = flt(
			same_task.reduce((sum, row) => sum + row.hours, 0),
			2
		);
		const names = same_task.map((row) => row.name).join(", ");
		lines.push(
			__("{0} already has {1}h on this task for {2} ({3}). With this allocation: {4}h.", [
				who,
				earlier,
				period,
				names,
				flt(earlier + hours, 2),
			])
		);
		color = "orange";
	}

	const total = flt(allocated + hours, 2);
	if (available === null) {
		lines.push(
			__("{0}h allocated in {1} across all tasks. Available time is unknown.", [
				total,
				period,
			])
		);
		return { lines, color: color === "green" ? "blue" : color };
	}
	const free = flt(available - total, 2);
	lines.push(
		free < 0
			? __("{0} is {1}h over in {2}: {3}h available, {4}h allocated across all tasks.", [
					who,
					-free,
					period,
					available,
					total,
			  ])
			: __("{0} has {1}h free in {2}: {3}h available, {4}h allocated across all tasks.", [
					who,
					free,
					period,
					available,
					total,
			  ])
	);
	return { lines, color: free < 0 ? "orange" : color };
}
