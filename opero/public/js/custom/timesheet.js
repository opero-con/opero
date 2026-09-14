// Opero: client scripts for Timesheet
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// Hide Personnel (employee_name) on the form only. Keep the field unhidden in
// meta so Report/List export can still include it (export pickers skip df.hidden).
frappe.ui.form.on("Timesheet", {
	refresh: function (frm) {
		frm.toggle_display("employee_name", false);
	},
});

// --- Auto Height Note: TS ---
frappe.ui.form.on("Timesheet", {
	onload: function (frm) {
		// Inject dynamic CSS if not already present
		if (!document.getElementById("resize-note-css")) {
			const style = document.createElement("style");
			style.id = "resize-note-css";
			style.innerHTML = `
                .frappe-control[data-fieldname="note"] .ql-editor {
                    min-height: 0px !important;
                    padding: 6px 12px;
                    overflow-y: hidden;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                    word-break: break-word;
                }
                .frappe-control[data-fieldname="note"] {
                    transition: height 0.2s ease;
                }
            `;
			document.head.appendChild(style);
		}

		// Resize logic with 2 extra lines (approx 44px)
		function resizeNoteEditor() {
			const editor = frm.fields_dict.note?.$wrapper.find(".ql-editor")[0];
			if (editor) {
				const lineHeight = 22; // Approx line height in pixels
				const extraPadding = lineHeight * 2;

				editor.style.height = "auto";
				editor.style.height = editor.scrollHeight + extraPadding + "px";
			}
		}

		setTimeout(resizeNoteEditor, 500); // Initial resize
		frm.fields_dict.note?.$wrapper.find(".ql-editor").on("input", resizeNoteEditor);
	},
});

// --- TS: Auto-fill Project Info and Sync Activity Type (Safe for Submit) ---
// Doctype: Timesheet  |  Script Type: Client Script
// Goal: Keep child "activity_type" (labelled "Project Rate Factor") aligned with parent_project
// Notes:
//  • Uses frm.allowed_activity_types as cache
//  • If exactly one type is allowed → auto-fill blanks deterministically
//  • On project change → re-fetch, re-filter, validate/repair all rows
//  • custom_pb_rate (parent field) remains a bulk-set convenience

function set_child_link_query(frm) {
	if (!frm.fields_dict || !frm.fields_dict.time_logs || !frm.fields_dict.time_logs.grid) {
		return;
	}
	frm.set_query("activity_type", "time_logs", function (doc) {
		var allowed = Array.isArray(frm.allowed_activity_types) ? frm.allowed_activity_types : [];
		if ((allowed || []).length > 0) {
			return { filters: [["Activity Type", "name", "in", allowed]] };
		}
		var filters = [];
		if (doc.parent_project) {
			filters.push(["Activity Type", "custom_project", "=", doc.parent_project]);
		} else {
			// Policy choice when no project selected:
			// Return empty result to discourage accidental picks.
			filters.push(["Activity Type", "name", "in", []]);
		}
		return { filters: filters };
	});
}

function fetch_allowed_activity_types(frm, done) {
	var project = (frm.doc.parent_project || "").trim();
	frm.allowed_activity_types = [];
	if (!project) {
		if (typeof done === "function") {
			done();
		}
		return;
	}
	frappe.db
		.get_list("Activity Type", {
			fields: ["name"],
			filters: { custom_project: project },
			order_by: "name asc",
			limit: 500,
		})
		.then(function (rows) {
			if (frm.doc.parent_project !== project) {
				return;
			}
			var seen = {};
			var unique = [];
			var i = 0;
			while (i < (rows || []).length) {
				var r = rows[i];
				var n = r && r.name ? String(r.name) : "";
				if (n && !seen[n]) {
					seen[n] = true;
					unique.push(n);
				}
				i = i + 1;
			}
			frm.allowed_activity_types = unique;
			if (typeof done === "function") {
				done();
			}
		})
		.catch(function () {
			if (frm.doc.parent_project !== project) {
				return;
			}
			frappe.show_alert({
				message: __(
					"Could not load project rate factors. Please reload before editing them."
				),
				indicator: "orange",
			});
		});
}

function value_is_allowed(value, allowed) {
	var i = 0;
	while (i < (allowed || []).length) {
		if (allowed[i] === value) {
			return true;
		}
		i = i + 1;
	}
	return false;
}

function apply_rules_to_row(frm, cdt, cdn) {
	if (frm.doc.docstatus !== 0) {
		return;
	}
	var d = frappe.get_doc(cdt, cdn);
	var allowed = frm.allowed_activity_types || [];
	var unique_pick = "";
	if ((allowed || []).length === 1) {
		unique_pick = allowed[0];
	}

	var current = (d.activity_type || "").trim();

	// Rule 1: if exactly one allowed and cell blank → set it
	if (!current && unique_pick) {
		frappe.model.set_value(cdt, cdn, "activity_type", unique_pick);
		return;
	}

	// Rule 2: if there is a value but not allowed for this project → clear it
	if (current && !value_is_allowed(current, allowed)) {
		frappe.model.set_value(cdt, cdn, "activity_type", "");
	}
}

function update_all_rows(frm) {
	var table = frm.doc.time_logs || [];
	var i = 0;
	while (i < table.length) {
		apply_rules_to_row(frm, table[i].doctype, table[i].name);
		i = i + 1;
	}
	frm.refresh_field("time_logs");
}

function bulk_set_from_parent_rate(frm) {
	// Applies frm.doc.custom_pb_rate to all rows (draft only)
	if (frm.doc.docstatus !== 0) {
		return;
	}
	if (!frm.doc.time_logs || frm.doc.time_logs.length === 0) {
		return;
	}
	var rate = frm.doc.custom_pb_rate || "";
	var i = 0;
	while (i < frm.doc.time_logs.length) {
		var row = frm.doc.time_logs[i];
		frappe.model.set_value(row.doctype, row.name, "activity_type", rate);
		i = i + 1;
	}
	frm.refresh_field("time_logs");
}

frappe.ui.form.on("Timesheet", {
	onload: function (frm) {
		set_child_link_query(frm);
		if (frm.doc.parent_project) {
			fetch_allowed_activity_types(frm, function () {
				set_child_link_query(frm);
				update_all_rows(frm);
			});
		}
	},

	refresh: function (frm) {
		set_child_link_query(frm);
	},

	parent_project: function (frm) {
		if (frm.doc.parent_project) {
			fetch_allowed_activity_types(frm, function () {
				set_child_link_query(frm);
				update_all_rows(frm);
			});
		} else {
			frm.allowed_activity_types = [];
			set_child_link_query(frm);
			update_all_rows(frm); // clears disallowed values when project is removed
		}
	},

	custom_pb_rate: function (frm) {
		// Keep your convenience bulk-set behaviour (draft only)
		bulk_set_from_parent_rate(frm);
	},
});

frappe.ui.form.on("Timesheet Detail", {
	time_logs_add: function (frm, cdt, cdn) {
		// Ensure cache exists before applying rules
		var ensure = function () {
			apply_rules_to_row(frm, cdt, cdn);
			frm.refresh_field("time_logs");
		};
		if (frm.allowed_activity_types === undefined) {
			fetch_allowed_activity_types(frm, function () {
				set_child_link_query(frm);
				ensure();
			});
		} else {
			ensure();
		}
	},
});

// --- Total Spent Hrs ---
frappe.ui.form.on("Timesheet", {
	employee: function (frm) {
		update_total_spent_hours(frm);
	},
	parent_project: function (frm) {
		update_total_spent_hours(frm);
	},
});

async function update_total_spent_hours(frm) {
	const employee = frm.doc.employee;
	const project = frm.doc.parent_project;
	if (!employee || !project) {
		if (frm.doc.docstatus === 0) await frm.set_value("custom_total_spent_hours", 0);
		return;
	}
	const total = await frappe.xcall("opero.api.timesheet.get_total_spent_hours", {
		employee,
		project,
	});
	if (frm.doc.employee !== employee || frm.doc.parent_project !== project) return;
	if (frm.doc.docstatus === 0) await frm.set_value("custom_total_spent_hours", total);
	else frm.get_field?.("custom_total_spent_hours")?.set_input(total);
}

frappe.ui.form.on("Timesheet", {
	refresh(frm) {
		update_total_spent_hours(frm);
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Split at midnight"), async () => {
				for (const row of [...(frm.doc.time_logs || [])]) {
					if (!row.from_time || !row.hours || row.hours <= 0) continue;
					// Use local wall-clock arithmetic, matching Frappe's stored datetimes.
					const start = moment(row.from_time);
					const end = start.clone().add(row.hours, "hours");
					let boundary = start.clone().startOf("day").add(1, "day");
					if (!end.isAfter(boundary)) continue;
					const template = {};
					for (const field of frappe.get_meta("Timesheet Detail").fields) {
						if (
							!["from_time", "to_time", "hours"].includes(field.fieldname) &&
							!field.fieldname.startsWith("zoho_") &&
							!field.fieldname.startsWith("custom_zoho_")
						) {
							template[field.fieldname] = row[field.fieldname];
						}
					}
					await frappe.model.set_value(row.doctype, row.name, {
						hours: boundary.diff(start, "seconds") / 3600,
						to_time: boundary.format("YYYY-MM-DD HH:mm:ss"),
					});
					while (boundary.isBefore(end)) {
						const segmentStart = boundary.clone();
						boundary = moment.min(boundary.clone().add(1, "day"), end);
						frm.add_child("time_logs", {
							...template,
							from_time: segmentStart.format("YYYY-MM-DD HH:mm:ss"),
							to_time: boundary.format("YYYY-MM-DD HH:mm:ss"),
							hours: boundary.diff(segmentStart, "seconds") / 3600,
						});
					}
				}
				frm.refresh_field("time_logs");
				frm.dirty();
			});
		}
		if (
			frm.doc.docstatus > 0 &&
			["Pending", "Failed", "Partial"].includes(frm.doc.custom_zoho_sync_status)
		) {
			frm.add_custom_button(__("Retry Zoho sync"), async () => {
				await frappe.xcall("opero.zoho_books.retry_timesheet_sync", {
					timesheet_name: frm.doc.name,
				});
				await frm.reload_doc();
			});
		}
	},
});

frappe.ui.form.on("Timesheet", {
	refresh(frm) {
		const uncertain = (frm.doc.time_logs || []).filter(
			(row) => row.custom_zoho_sync_uncertain
		);
		if (!["Failed", "Partial"].includes(frm.doc.custom_zoho_sync_status) || !uncertain.length)
			return;
		frm.add_custom_button(__("Resolve Zoho entry"), () => {
			frappe.prompt(
				[
					{
						fieldname: "row_number",
						label: __("Row number"),
						fieldtype: "Int",
						reqd: 1,
						default: uncertain[0].idx,
					},
					{
						fieldname: "remote_id",
						label: __("Existing Zoho time entry ID"),
						fieldtype: "Data",
					},
					{
						fieldname: "confirmed_absent",
						label: __("I checked Zoho and confirmed this entry is absent"),
						fieldtype: "Check",
					},
				],
				async (values) => {
					await frappe.xcall("opero.zoho_books.reconcile_timesheet_entry", {
						timesheet_name: frm.doc.name,
						...values,
					});
					await frm.reload_doc();
				},
				__("Check Zoho before resolving this entry"),
				__("Resolve")
			);
		});
	},
});

const refresh_allocation_balances = frappe.utils.debounce(async (frm) => {
	frm.dashboard.parent.find(".opero-allocation").remove();
	if (frm.doc.docstatus !== 0 || !frm.doc.employee || !frm.doc.parent_project) return;
	const snapshot = JSON.stringify({
		name: frm.doc.name,
		employee: frm.doc.employee,
		project: frm.doc.parent_project,
		rows: (frm.doc.time_logs || []).map((row) => ({
			task: row.task,
			from_time: row.from_time,
			hours: row.hours,
		})),
	});
	const request = JSON.parse(snapshot);
	const balances = await frappe.xcall("opero.api.timesheet.get_allocation_balances", {
		employee: request.employee,
		project: request.project,
		time_logs: request.rows,
		timesheet_name: frm.is_new() ? null : frm.doc.name,
	});
	const current = JSON.stringify({
		name: frm.doc.name,
		employee: frm.doc.employee,
		project: frm.doc.parent_project,
		rows: (frm.doc.time_logs || []).map((row) => ({
			task: row.task,
			from_time: row.from_time,
			hours: row.hours,
		})),
	});
	if (snapshot !== current || frm.doc.docstatus !== 0) return;
	const escape = frappe.utils.escape_html;
	frm.dashboard.parent.find(".opero-allocation").remove();
	frm.dashboard.show();
	frm.dashboard.add_section(
		`<table class="table table-bordered"><thead><tr>
        <th>${__("Task / Month")}</th><th>${__("Allocated")}</th><th>${__("Submitted")}</th>
        <th>${__("This timesheet")}</th><th>${__(
			"Remaining after this timesheet"
		)}</th></tr></thead><tbody>
        ${balances
			.map(
				(row) => `<tr><td>${escape(row.task)} / ${escape(row.month)}</td>
        <td>${row.allocated}</td><td>${row.submitted}</td><td>${row.current}</td>
        <td class="${row.remaining < 0 ? "text-danger" : ""}">${row.remaining}</td></tr>`
			)
			.join("")}
        </tbody></table>`,
		__("Monthly allocation"),
		"custom opero-allocation"
	);
}, 300);

frappe.ui.form.on("Timesheet", {
	refresh: refresh_allocation_balances,
	employee: refresh_allocation_balances,
	parent_project: refresh_allocation_balances,
});
frappe.ui.form.on("Timesheet Detail", {
	task: refresh_allocation_balances,
	from_time: refresh_allocation_balances,
	hours: refresh_allocation_balances,
	time_logs_remove: refresh_allocation_balances,
});
