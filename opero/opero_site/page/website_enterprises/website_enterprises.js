frappe.pages["website-enterprises"].on_page_show = function () {
	frappe.set_route("List", "Enterprise", { show_on_website: 1 }).then(() => {
		// Keep this page's filter from leaking into later Enterprise navigation.
		frappe.route_options = null;
	});
};
