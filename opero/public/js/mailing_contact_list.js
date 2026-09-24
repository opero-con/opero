{
	const settings = frappe.listview_settings.Contact || {};
	const native_onload = settings.onload;
	settings.onload = function (listview) {
		if (native_onload) native_onload(listview);
		listview.page.add_action_item(__("Manage Mailing Lists"), () => {
			opero.mailing.bulk(listview.get_checked_items().map((c) => c.name), () => listview.refresh());
		});
		if (frappe.model.can_export("Contact")) {
			listview.page.add_menu_item(__("Export with Mailing List status"), () => {
				const args = listview.get_args();
				open_url_post("/api/method/opero.mailing.filters.export_contacts", {
					filters: JSON.stringify(args.filters || []), or_filters: JSON.stringify(args.or_filters || []),
				});
			});
		}
	};
	frappe.listview_settings.Contact = settings;
}
