// Copyright (c) 2026, Patrick Willy and contributors
// For license information, please see license.txt

frappe.query_reports["Weekly Hours"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			get_query: () => {
				const company = frappe.query_report.get_filter_value("company");
				return company ? { filters: { company } } : {};
			},
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "include_awaiting_approval",
			label: __("Include awaiting approval"),
			fieldtype: "Check",
		},
	],
	formatter(value, row, column, data, default_formatter) {
		const formatted = default_formatter(value, row, column, data);
		const fieldname = column.fieldname || "";
		const expected = data && data[fieldname.replace(/^week_/, "expected_")];
		const is_short_week = fieldname.startsWith("week_") && expected != null && value < expected;
		const is_short_total = fieldname === "difference" && value < 0;
		if (fieldname === "personnel" && data && data.employee) {
			return frappe.utils.get_form_link("Employee", data.employee, true, formatted);
		}
		return is_short_week || is_short_total ? `<span class="text-danger">${formatted}</span>` : formatted;
	},
};
