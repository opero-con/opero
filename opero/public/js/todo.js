const extractPlainText = (value) => {
	const text = frappe.utils.unescape_html(strip_html(cstr(value || "")))
	return text.replace(/\s+/g, " ").trim()
}

const STATUS_TONE_ICON = {
	danger: "🔴",
	warning: "🟠",
	primary: "🔵",
	success: "🟢",
	neutral: "⚪",
}

const withToneIcon = (label, tone) => {
	const icon = STATUS_TONE_ICON[tone] || STATUS_TONE_ICON.neutral
	return `${icon} ${label}`
}

const getStatusVsDueDateDescriptor = (statusLabel, statusDateValue, dueDateValue) => {
	const dueDate = cstr(dueDateValue || "").trim()
	if (!dueDate) {
		return { label: __(statusLabel), tone: "neutral" }
	}

	const statusDate = cstr(statusDateValue || "").trim()
	if (!statusDate) {
		return { label: __(statusLabel), tone: "neutral" }
	}

	const statusDateOnly = statusDate.split(" ")[0]
	const dayDiff = frappe.datetime.get_diff(statusDateOnly, dueDate)

	if (dayDiff === 0) {
		return { label: __("{0} on due date", [statusLabel]), tone: "primary" }
	}
	if (dayDiff < 0) {
		return {
			label: __("{0} {1}d before due date", [statusLabel, Math.abs(dayDiff)]),
			tone: "success",
		}
	}
	return { label: __("{0} {1}d after due date", [statusLabel, dayDiff]), tone: "danger" }
}

const getDueDateDescriptor = (doc) => {
	const status = cstr(doc.status || "").trim()
	if (status === "Closed") {
		return getStatusVsDueDateDescriptor("Closed", doc.custom_closed_on, doc.date)
	}
	if (status === "Cancelled") {
		return getStatusVsDueDateDescriptor("Cancelled", doc.custom_cancelled_on, doc.date)
	}

	const dueDate = cstr(doc.date || "").trim()
	if (!dueDate) {
		return null
	}

	const dayDiff = frappe.datetime.get_diff(dueDate, frappe.datetime.get_today())
	if (dayDiff === 0) {
		return { label: __("Due today"), tone: "warning" }
	}
	if (dayDiff === 1) {
		return { label: __("Due tomorrow"), tone: "warning" }
	}
	if (dayDiff > 1) {
		return { label: __("Due in {0} days", [dayDiff]), tone: "success" }
	}
	if (dayDiff === -1) {
		return { label: __("Overdue by 1 day"), tone: "danger" }
	}
	return { label: __("Overdue by {0} days", [Math.abs(dayDiff)]), tone: "danger" }
}

const setDueDateDescription = (frm) => {
	const descriptor = getDueDateDescriptor(frm.doc)
	const description = descriptor ? withToneIcon(descriptor.label, descriptor.tone) : ""
	frm.set_df_property("date", "description", description)
}

frappe.ui.form.on("ToDo", {
	refresh(frm) {
		frm.toggle_display("allocated_to", false)
		frm.set_query("custom_allocatees", () => ({
			filters: {
				enabled: 1,
			},
		}))
		setDueDateDescription(frm)
		frm.add_custom_button(__("Flow Hub"), () => frappe.set_route("flow-hub"))
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

	status(frm) {
		setDueDateDescription(frm)
	},
})
