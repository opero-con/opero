// Redirect /app/flow-hub (the Flow Hub workspace sidebar entry)
// → /app/opero-flow-hub (the actual Flow Hub HTML page).
// This fires on every route change, so clicking "Flow Hub" in the sidebar
// transparently lands the user on the rich HTML page.
$(document).on("page-change", function () {
	if (frappe.get_route_str && frappe.get_route_str() === "flow-hub") {
		frappe.set_route("opero-flow-hub");
	}
});
