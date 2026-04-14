const extractPlainText = (value) => {
	const text = frappe.utils.unescape_html(strip_html(cstr(value || "")))
	return text.replace(/\s+/g, " ").trim()
}

frappe.ui.form.on("ToDo", {
	refresh(frm) {
		frm.toggle_display("allocated_to", false)
		frm.toggle_display("custom_additional_assignees", false)
		frm.set_query("custom_assignees", () => ({
			filters: {
				enabled: 1,
			},
		}))
	},

	custom_title(frm) {
		const title = extractPlainText(frm.doc.custom_title)
		if (title && title !== cstr(frm.doc.custom_title || "").trim()) {
			frm.set_value("custom_title", title)
			return
		}
	},

	description(frm) {
		const description = extractPlainText(frm.doc.description)
		if (description && !extractPlainText(frm.doc.custom_title)) {
			frm.set_value("custom_title", description)
		}
	},
})
