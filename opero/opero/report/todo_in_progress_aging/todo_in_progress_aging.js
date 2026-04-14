frappe.query_reports["ToDo In Progress Aging"] = {
	filters: [
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
			default: ["In Progress"],
			get_data: function (txt) {
				const options = ["Open", "In Progress", "Closed", "Cancelled"];
				const query = (txt || "").toLowerCase();
				return options
					.filter((status) => status.toLowerCase().includes(query))
					.map((status) => ({ value: status, description: "" }));
			},
		},
		{
			fieldname: "min_days",
			label: __("Min Idle Days"),
			fieldtype: "Int",
			default: 7,
		},
		{
			fieldname: "only_overdue",
			label: __("Only Overdue"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: "show_all",
			label: __("Show Team Scope"),
			fieldtype: "Check",
			default: 0,
			description: __("Includes all matching ToDos instead of only your scope."),
		},
	],
};
