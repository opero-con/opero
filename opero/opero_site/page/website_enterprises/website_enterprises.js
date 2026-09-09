frappe.pages["website-enterprises"].on_page_show = function () {
	frappe.route_options = { show_on_website: 1 };
	frappe.set_route("List", "Enterprise");
};
