frappe.query_reports["ToDo Created vs Closed"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
		{
			fieldname: "time_window",
			label: __("Window"),
			fieldtype: "Select",
			options: [
				"Last 30 Days",
				"Last 90 Days",
				"Last 180 Days",
				"Last 365 Days",
				"Last 730 Days",
			],
			default: "Last 30 Days",
		},
		{
			fieldname: "granularity",
			label: __("View"),
			fieldtype: "Select",
			options: ["Auto", "Day", "Week", "Month"],
			default: "Auto",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			description: __("Overrides the Window selector"),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
	],
};
