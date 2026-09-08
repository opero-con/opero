{
	const settings = frappe.listview_settings.Contact || {};
	const native_onload = settings.onload;
	settings.onload = function (listview) {
		if (native_onload) native_onload(listview);
		listview.opero_mailing_filter = {};
		const native_args = listview.get_args.bind(listview);
		listview.get_args = function () {
			const args = native_args();
			args.opero_mailing_filter = JSON.stringify(this.opero_mailing_filter || {});
			return args;
		};
		const native_count = listview.get_count_str.bind(listview);
		listview.get_count_str = async function () {
			if (!this.opero_mailing_filter.mailing_lists?.length && !this.opero_mailing_filter.status) return native_count();
			const count = await frappe.xcall("frappe.desk.reportview.get_count", {
				doctype: "Contact", fields: [], filters: this.get_filters_for_args(), distinct: true,
				opero_mailing_filter: JSON.stringify(this.opero_mailing_filter),
			});
			this.total_count = count;
			return __("{0} of {1}", [this.data.length, count]);
		};
		const button = listview.page.add_inner_button(__("Mailing List filters"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Filter Contacts by Mailing Lists"),
				fields: [opero.mailing.group_field(),
					{ fieldname: "match", label: __("Match lists"), fieldtype: "Select", options: "Any\nAll", default: "Any" },
					{ fieldname: "status", label: __("Membership status"), fieldtype: "Select", options: "\nConfirmed\nUnsubscribed\nNo email" },
					{ fieldtype: "HTML", options: `<p>${__("Status applies to each selected list. All requires every selected membership to match.")}</p>` }],
				primary_action_label: __("Apply filters"),
				primary_action(values) {
					listview.opero_mailing_filter = values;
					const active = values.mailing_lists?.length || values.status;
					button.toggleClass("btn-info", !!active);
					button.text(active ? __("Mailing List filters (active)") : __("Mailing List filters"));
					d.hide(); listview.start = 0; listview.refresh();
				},
				secondary_action_label: __("Clear mailing filters"),
				secondary_action() {
					listview.opero_mailing_filter = {};
					button.removeClass("btn-info").text(__("Mailing List filters"));
					d.hide(); listview.start = 0; listview.refresh();
				},
			});
			d.set_values(listview.opero_mailing_filter); d.show();
		});
		listview.page.add_action_item(__("Manage Mailing Lists"), () => {
			opero.mailing.bulk(listview.get_checked_items().map((c) => c.name), () => listview.refresh());
		});
		if (frappe.model.can_export("Contact")) {
			listview.page.add_menu_item(__("Export with Mailing List status"), () => {
				const args = listview.get_args();
				open_url_post("/api/method/opero.mailing.filters.export_contacts", {
					filters: JSON.stringify(args.filters || []), or_filters: JSON.stringify(args.or_filters || []),
					mailing_filter: args.opero_mailing_filter,
				});
			});
		}
	};
	frappe.listview_settings.Contact = settings;
}
