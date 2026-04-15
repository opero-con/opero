frappe.query_reports["ToDo Assignee Load and Risk"] = {
	filters: [
		{
			fieldname: "assignee",
			label: __("Assignee"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "include_disabled_users",
			label: __("Include Disabled Users"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: "top_n",
			label: __("Top N (Chart)"),
			fieldtype: "Int",
			default: 10,
		},
		{
			fieldname: "include_historical",
			label: __("Include All History"),
			fieldtype: "Check",
			default: 0,
		},
	],
};
