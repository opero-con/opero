frappe.ui.form.on("Publication", {
	refresh(frm) {
		show_website_link(frm);
		const field = frm.get_field("summary");
		if (field && field.$input && !field.$input.data("opero-autosize")) {
			field.$input.data("opero-autosize", 1);
			field.$input.on("input", () => fit_summary(frm));
		}
		fit_summary(frm);
	},
	summary(frm) {
		fit_summary(frm);
	},
});

function show_website_link(frm) {
	const field = frm.get_field("website_link");
	if (!field) {
		return;
	}
	const has_url = !!frm.doc.slug && !frm.doc.__islocal;
	frm.toggle_display("website_link", has_url);
	if (!has_url) {
		field.$wrapper.empty();
		return;
	}
	const address = `opero-services.com/publications/${encodeURIComponent(frm.doc.slug)}`;
	field.$wrapper
		.empty()
		.append($("<div>", { class: "control-label", text: __("URL") }))
		.append(
			$("<a>", {
				href: `https://${address}.html`,
				text: address,
				target: "_blank",
				rel: "noopener noreferrer",
			})
		);
}

// Fit the text plus one spare line, so an empty summary shows two lines.
function fit_summary(frm) {
	const field = frm.get_field("summary");
	const input = field && field.$input && field.$input.get(0);
	if (!input) {
		return;
	}
	input.rows = 1;
	input.style.overflowY = "hidden";
	input.style.resize = "none";
	input.style.height = "auto";
	const line_height = parseFloat(getComputedStyle(input).lineHeight);
	input.style.height = `${input.scrollHeight + line_height}px`;
}
