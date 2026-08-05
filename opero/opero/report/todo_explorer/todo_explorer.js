frappe.query_reports["ToDo Explorer"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
		{
			fieldname: "assignee",
			label: __("Assignee"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "MultiSelectList",
			get_data: function (txt) {
				const options = ["Open", "In Progress", "Closed", "Cancelled"];
				const query = (txt || "").toLowerCase();
				return options
					.filter((s) => s.toLowerCase().includes(query))
					.map((s) => ({ value: s, description: "" }));
			},
		},
		{
			fieldname: "priority",
			label: __("Priority"),
			fieldtype: "MultiSelectList",
			get_data: function (txt) {
				const options = ["Urgent", "High", "Medium", "Low"];
				const query = (txt || "").toLowerCase();
				return options
					.filter((p) => p.toLowerCase().includes(query))
					.map((p) => ({ value: p, description: "" }));
			},
		},
		{
			fieldname: "from_date",
			label: __("Due Date From"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("Due Date To"),
			fieldtype: "Date",
		},
		{
			fieldname: "show_only_overdue",
			label: __("Only Overdue"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: "unassigned_only",
			label: __("Unassigned Only"),
			fieldtype: "Check",
			default: 0,
		},
	],
};
