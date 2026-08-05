// Opero: query-report client behaviour for Resource Planner reports
// Migrated from Frappe Cloud Client Scripts (enabled Report Form scripts).
// Loaded via app_include_js so handlers exist before query reports open.

frappe.provide("frappe.query_reports");

// --- Description on Resource Planner with Project Filter ---
frappe.query_reports["Resource Planner with Project Filter-Beta"] = {
	onload(report) {
		setTimeout(() => {
			$(".custom-info-box").remove();
			const infoBox = $(`<div class="custom-info-box alert alert-info" style="margin-top: 10px;">
				<strong>Note:</strong> This report shows personnel allocation per month relative to standard working hours.<br>
				<span style="color:red;">Red</span> = 0%, <span style="color:blue;">Blue</span> = current month. Click on values to drill down.
			</div>`);
			$(".layout-main-section").prepend(infoBox);
		}, 500);
	},
};

// --- Drill-Down (Resource Planner V3) ---
frappe.query_reports["Resource Planner V3"] = {
	onload(report) {
		report.page.add_inner_button(__("View Task Details"), () => {
			const filters = report.get_values();
			frappe.set_route("query-report", "Task Time Distribution Report", {
				year: filters.year || "2024",
			});
		});
	},

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname !== "Personnel" && value && value !== "0.00") {
			const personnel = frappe.utils.escape_html(data.Personnel || "");
			const label = frappe.utils.escape_html(column.label || "");
			return `<a href="#" onclick="opero_open_ttd_report('${personnel}', '${label}'); return false;">${value}</a>`;
		}
		return value;
	},
};

window.opero_open_ttd_report = function (personnel, month) {
	const report_settings = frappe.query_reports["Resource Planner V3"] || {};
	const year_filter = (report_settings.filters || []).find((f) => f.fieldname === "year");
	const year = year_filter ? year_filter.value : "2024";
	const month_abbr = (month || "").substring(0, 3).trim();

	frappe.set_route("query-report", "Task Time Distribution Report", {
		personnel: personnel,
		month: month_abbr,
		year: year,
		apply_filters: 1,
	});

	let retries = 10;
	const applyFilters = setInterval(() => {
		if (frappe.query_report && frappe.query_report.get_filter) {
			const personnel_filter = frappe.query_report.get_filter("personnel");
			const month_filter = frappe.query_report.get_filter("month");
			const year_filter = frappe.query_report.get_filter("year");

			if (personnel_filter && month_filter && year_filter) {
				clearInterval(applyFilters);
				frappe.query_report.set_filter_value("personnel", personnel);
				frappe.query_report.set_filter_value("month", month_abbr);
				frappe.query_report.set_filter_value("year", year);
				setTimeout(() => frappe.query_report.refresh(), 500);
			}
		}

		retries -= 1;
		if (retries <= 0) {
			clearInterval(applyFilters);
		}
	}, 500);
};
