frappe.ui.form.on("Publication", {
	refresh(frm) {
		show_pdf_rename(frm);
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
	file_url(frm) {
		show_pdf_rename(frm);
	},
});

// Rename the PDF already stored on the publication. Sidebar attachments are separate files.
function show_pdf_rename(frm) {
	if (!frm.doc) {
		return;
	}
	const field = frm.get_field("file_url");
	if (!field || !field.$wrapper) {
		return;
	}
	field.$wrapper.find(".pdf-rename").remove();
	const url = frm.doc.file_url || "";
	const on_desk = url.startsWith("/files/") || url.startsWith("/private/files/");
	if (!on_desk || frm.doc.__islocal) {
		return;
	}
	const button = $("<button>", {
		type: "button",
		class: "btn btn-xs btn-default",
		text: __("Rename"),
	});
	button.on("click", () => prompt_pdf_rename(frm));
	field.$wrapper.append(
		$("<div>", { class: "pdf-rename", style: "margin-top: 8px" }).append(button)
	);
}

function prompt_pdf_rename(frm) {
	if (frm.is_dirty && frm.is_dirty()) {
		frappe.msgprint(__("Save the publication before renaming its PDF."));
		return;
	}
	let current = (frm.doc.file_url || "").split("/").pop() || "";
	try {
		current = decodeURIComponent(current);
	} catch (error) {
		// Keep the stored name when it is not encoded.
	}
	frappe.prompt(
		{
			fieldname: "filename",
			fieldtype: "Data",
			label: __("File name"),
			reqd: 1,
			default: current,
			description: __("The public page uses this name after the next deploy."),
		},
		(values) => {
			frappe.call({
				method: "opero.opero_site.doctype.publication.publication.rename_publication_pdf",
				args: { name: frm.doc.name, filename: values.filename },
				freeze: true,
				freeze_message: __("Renaming the PDF"),
				callback() {
					frm.reload_doc();
				},
			});
		},
		__("Rename PDF"),
		__("Rename")
	);
}

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
