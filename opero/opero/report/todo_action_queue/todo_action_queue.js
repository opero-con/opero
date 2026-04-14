frappe.query_reports["ToDo Action Queue"] = {
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
			get_data: function (txt) {
				const options = ["Open", "In Progress", "Closed", "Cancelled"];
				const query = (txt || "").toLowerCase();
				return options
					.filter((status) => status.toLowerCase().includes(query))
					.map((status) => ({ value: status, description: "" }));
			},
		},
		{
			fieldname: "priority",
			label: __("Priority"),
			fieldtype: "Select",
			options: ["", "Low", "Medium", "High", "Urgent"],
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
	],
};
