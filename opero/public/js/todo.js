frappe.ui.form.on("ToDo", {
	custom_title(frm) {
		if (frm.doc.custom_title && !frm.doc.description) {
			frm.set_value("description", frm.doc.custom_title)
		}
	},

	description(frm) {
		if (frm.doc.description && !frm.doc.custom_title) {
			frm.set_value("custom_title", frm.doc.description)
		}
	},

	custom_additional_assignees(frm) {
		if (!frm.doc.custom_additional_assignees) {
			return
		}

		const normalized = [
			...new Set(
				frm.doc.custom_additional_assignees
					.split(/[\n,;]+/)
					.map((value) => value.trim())
					.filter(Boolean)
			),
		].join("\n")

		if (normalized !== frm.doc.custom_additional_assignees) {
			frm.set_value("custom_additional_assignees", normalized)
		}
	},
})
