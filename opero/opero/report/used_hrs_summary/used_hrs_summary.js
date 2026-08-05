// Copyright (c) 2026, Patrick Willy and contributors
// For license information, please see license.txt

frappe.query_reports["Used Hrs Summary"] = {
	filters: [
		{
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Int",
			default: frappe.datetime.get_today().slice(0, 4),
			reqd: 1,
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",
		},
	],
};
