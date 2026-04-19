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

const renderAllocateesSidebar = (frm) => {
	frm.assign_to.parent.siblings(".opero-allocatees-section").remove()

	if (frm.doc.__islocal) return

	const $section = $(`
		<ul class="list-unstyled sidebar-menu opero-allocatees-section">
			<li>
				<span class="form-sidebar-items">
					<span>
						<svg class="es-icon ml-0 icon-sm"><use href="#es-line-add-people"></use></svg>
						<span class="ellipsis">${__("Allocatees")}</span>
					</span>
					<button class="opero-add-allocatee-btn btn btn-link icon-btn">
						<svg class="es-icon icon-sm"><use href="#es-line-add"></use></svg>
					</button>
				</span>
				<div class="opero-allocatees-list"></div>
			</li>
		</ul>
	`)

	frm.assign_to.parent.after($section)

	const users = (frm.doc.custom_allocatees || []).map(r => r.user).filter(Boolean)
	if (users.length) {
		const avatarGroup = frappe.avatar_group(users, 5, { align: "left", overlap: true })
		$section.find(".opero-allocatees-list").append(avatarGroup)
		avatarGroup.click(() => openAllocateesDialog(frm))
	}

	$section.find(".opero-add-allocatee-btn").on("click", () => openAllocateesDialog(frm))
}

const openAllocateesDialog = (frm) => {
	let adding = false

	const dialog = new frappe.ui.Dialog({
		title: __("Allocatees"),
		size: "small",
		no_focus: true,
		fields: [
			{
				label: __("Add a user"),
				fieldname: "user",
				fieldtype: "Link",
				options: "User",
				get_query: () => ({ filters: { enabled: 1, user_type: "System User" } }),
				change() {
					const value = dialog.get_value("user")
					if (!value || adding) return
					adding = true
					dialog.set_df_property("user", "read_only", 1)
					const currentRows = frm.doc.custom_allocatees || []
					if (currentRows.some(r => r.user === value)) {
						dialog.set_value("user", null)
						dialog.set_df_property("user", "read_only", 0)
						adding = false
						return
					}
					frm.set_value("custom_allocatees", [...currentRows, { user: value }])
					frm.save()
						.then(() => {
							dialog.set_value("user", null)
							refreshDialogList()
							renderAllocateesSidebar(frm)
						})
						.finally(() => {
							dialog.set_df_property("user", "read_only", 0)
							adding = false
						})
				},
			},
			{ fieldtype: "HTML", fieldname: "allocatees_list" },
		],
	})

	const refreshDialogList = () => {
		const $list = $(dialog.get_field("allocatees_list").wrapper)
		$list.removeClass("frappe-control").empty()

		;(frm.doc.custom_allocatees || []).forEach(row => {
			if (!row.user) return
			const $row = $(`
				<div class="dialog-assignment-row" data-user="${row.user}">
					<div class="assignee">
						${frappe.avatar(row.user)}
						${frappe.user.full_name(row.user)}
					</div>
					<div class="btn-group btn-group-sm">
						<button type="button" class="btn btn-default remove-allocatee-btn" title="${__("Remove")}">
							${frappe.utils.icon("close")}
						</button>
					</div>
				</div>
			`)
			$row.find(".remove-allocatee-btn").on("click", () => {
				const newRows = (frm.doc.custom_allocatees || []).filter(r => r.user !== row.user)
				frm.set_value("custom_allocatees", newRows)
				frm.save().then(() => {
					$row.remove()
					renderAllocateesSidebar(frm)
				})
			})
			$list.append($row)
		})
	}

	refreshDialogList()
	dialog.show()
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
		frm.add_custom_button(__("Flow Hub"), () => { window.location.href = "/app/flow-hub"; })
		renderAllocateesSidebar(frm)
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
