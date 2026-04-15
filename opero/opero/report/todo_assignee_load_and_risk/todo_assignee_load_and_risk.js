frappe.query_reports["ToDo Assignee Load and Risk"] = {
	formatter: function (value, row, column, data, default_formatter) {
		if (column.fieldname === "assignee" && value) {
			const label = frappe.utils.escape_html(data.assignee_name || value);
			const href = `/app/user/${encodeURIComponent(value)}`;
			return `<a href="${href}">${label}</a>`;
		}
		return default_formatter(value, row, column, data);
	},
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
			label: __("Assignees in Chart"),
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
