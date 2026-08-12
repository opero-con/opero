// Opero: client scripts for Project
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// --- Time_allocation_handler ---
frappe.ui.form.on("Project", {
	refresh(frm) {
		calculate_total_hours(frm);
		opero.project.render_hours_summary(frm);
	},
	custom_time_allocation_add(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		row.project = frm.doc.name;
		frm.refresh_field("custom_time_allocation");
		calculate_total_hours(frm);
	},
	custom_time_allocation_remove(frm) {
		calculate_total_hours(frm);
	},
	"custom_time_allocation.hours"(frm) {
		calculate_total_hours(frm);
	},
});

function calculate_total_hours(frm) {
	let total_hours = 0;
	$.each(frm.doc.custom_time_allocation || [], function (_i, row) {
		total_hours += row.hours ? parseFloat(row.hours) : 0;
	});
	frm.set_value("custom_total_project_allocated_hours", total_hours);
}

frappe.provide("opero.project");

opero.project._hours_summary_styles = false;

opero.project.ensure_hours_summary_styles = function () {
	if (opero.project._hours_summary_styles) return;
	opero.project._hours_summary_styles = true;
	const css = `
		.opero-hours-summary {
			display: inline-block;
			padding: 4px 0 8px;
			vertical-align: top;
			max-width: 100%;
		}
		.opero-hours-summary__bar {
			height: 8px;
			margin-bottom: 10px;
			background-color: var(--control-bg);
			border-radius: 4px;
			overflow: hidden;
		}
		.opero-hours-summary__fill {
			height: 100%;
			border-radius: 4px;
			background-color: var(--primary);
		}
		.opero-hours-summary__fill.is-over {
			background-color: var(--red-500, #e24c4c);
		}
		.opero-hours-summary__meta {
			display: block;
			font-size: var(--text-sm);
			white-space: nowrap;
			font-variant-numeric: tabular-nums;
		}
		.opero-hours-summary__meta strong {
			font-weight: 600;
		}
	`;
	$("<style data-opero-hours-summary>").text(css).appendTo("head");
};

opero.project.render_hours_summary = function (frm) {
	const field = frm.get_field("custom_hours_summary");
	if (!field) return;

	opero.project.ensure_hours_summary_styles();

	const allocated = flt(frm.doc.custom_allocated_hours);
	const used = flt(frm.doc.actual_time);
	const ratio = allocated > 0 ? (used / allocated) * 100 : 0;
	const pct = Math.max(0, Math.min(ratio, 100));
	const over = used > allocated && allocated > 0;
	const fmt = (n) => format_number(n, null, 2);
	const label =
		`${__("Used")} <strong>${fmt(used)}</strong>` +
		` <span class="${over ? "text-danger" : "text-muted"}">(${format_number(ratio, null, 1)}%)</span>` +
		` <span class="text-muted">·</span> ` +
		`${__("Allocated")} <strong>${fmt(allocated)}</strong>`;

	// Measure a detached label so the track matches the text, not the section.
	const $measure = $(`<div class="opero-hours-summary__meta">${label}</div>`).css({
		position: "absolute",
		visibility: "hidden",
		whiteSpace: "nowrap",
		left: "-9999px",
		top: "0",
	});
	$("body").append($measure);
	const width = Math.ceil($measure.outerWidth());
	$measure.remove();

	field.$wrapper.html(`
		<div class="opero-hours-summary" style="width: ${width}px;">
			<div class="opero-hours-summary__bar" style="width: ${width}px;">
				<div class="opero-hours-summary__fill${over ? " is-over" : ""}"
					style="width: ${pct}%;"></div>
			</div>
			<div class="opero-hours-summary__meta">${label}</div>
		</div>
	`);
};
