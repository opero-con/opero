const extractPlainText = (value) => {
	const text = frappe.utils.unescape_html(strip_html(cstr(value || "")))
	return text.replace(/\s+/g, " ").trim()
}

const getRelativeDueDateLabel = (value) => {
	const dueDate = cstr(value || "").trim()
	if (!dueDate) {
		return ""
	}

	const dayDiff = frappe.datetime.get_diff(dueDate, frappe.datetime.get_today())
	if (dayDiff === 0) {
		return __("Due today")
	}
	if (dayDiff === 1) {
		return __("Due tomorrow")
	}
	if (dayDiff > 1) {
		return __("Due in {0} days", [dayDiff])
	}
	if (dayDiff === -1) {
		return __("Overdue by 1 day")
	}
	return __("Overdue by {0} days", [Math.abs(dayDiff)])
}

const setDueDateDescription = (frm) => {
	const label = getRelativeDueDateLabel(frm.doc.date)
	frm.set_df_property("date", "description", label || "")
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
		setDueDateDescription(frm)
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

	date(frm) {
		setDueDateDescription(frm)
	},
})
