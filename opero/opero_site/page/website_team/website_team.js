frappe.pages["website-team"].on_page_show = function () {
	frappe.set_route("List", "Employee", { show_on_website: 1 }).then(() => {
		frappe.route_options = null;
	});
};
