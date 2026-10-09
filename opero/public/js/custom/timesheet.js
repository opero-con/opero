// Opero: client scripts for Timesheet
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// Hide unused form-only fields without changing ERPNext-owned DocType metadata.
// Keep Personnel and Workflow State unhidden in meta so Report/List views can
// include them (column pickers skip df.hidden). Hide them only in the form body.
frappe.ui.form.on("Timesheet", {
	refresh: function (frm) {
		frm.toggle_display("employee_name", false);
		frm.toggle_display("workflow_state", false);
		frm.toggle_display("start_date", false);
		frm.toggle_display("end_date", false);
		frm.toggle_display("department", false);
		frm.toggle_display("custom_total_spent_hours", false);
		frm.toggle_display("custom_pm_name", false);
		frm.dashboard.links_area.hide();
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
		const grid = frm.fields_dict?.time_logs?.grid;
		if (frm.doc.docstatus === 0 && grid?.update_docfield_property) {
			grid.update_docfield_property("from_time", "description", __("Choose the work date. Clock times are generated from 08:00."));
			grid.update_docfield_property("to_time", "read_only", 1);
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

function allocation_snapshot(frm) {
	return JSON.stringify({
		name: frm.doc.name,
		employee: frm.doc.employee,
		project: frm.doc.parent_project,
		rows: (frm.doc.time_logs || []).map((row) => ({
			task: row.task,
			from_time: row.from_time,
			hours: row.hours,
			project: row.project,
		})),
	});
}

function show_allocation_section(frm, body) {
	frm.dashboard.parent.find(".opero-allocation").remove();
	frm.dashboard.show();
	frm.dashboard.add_section(body, __("Allocations"), "custom opero-allocation");
}

function allocation_message(message, css_class = "text-muted") {
	return `<div class="${css_class} small">${frappe.utils.escape_html(message)}</div>`;
}

const refresh_allocation_balances = frappe.utils.debounce(async (frm) => {
	const request_id = (frm.__opero_allocation_request_id || 0) + 1;
	frm.__opero_allocation_request_id = request_id;
	if (frm.doc.docstatus === 2 || !frm.doc.employee) {
		frm.dashboard.parent.find(".opero-allocation").remove();
		return;
	}

	const snapshot = allocation_snapshot(frm);
	const request = JSON.parse(snapshot);
	show_allocation_section(frm, allocation_message(__("Loading allocations…")));

	let balances;
	try {
		balances = await frappe.xcall("opero.api.timesheet.get_allocation_balances", {
			employee: request.employee,
			project: request.project,
			time_logs: request.rows,
			timesheet_name: frm.is_new() ? null : frm.doc.name,
		});
	} catch (error) {
		if (frm.__opero_allocation_request_id !== request_id) return;
		show_allocation_section(
			frm,
			allocation_message(
				__("Could not load allocations. Change an entry or refresh the form to retry."),
				"text-danger"
			)
		);
		return;
	}

	if (
		frm.__opero_allocation_request_id !== request_id ||
		snapshot !== allocation_snapshot(frm) ||
		frm.doc.docstatus === 2
	)
		return;

	if (!Array.isArray(balances) || !balances.length) {
		show_allocation_section(
			frm,
			allocation_message(__("Add a task and date to see monthly allocation balances."))
		);
		return;
	}

	const escape = frappe.utils.escape_html;
	show_allocation_section(
		frm,
		`<div class="table-responsive"><table class="table table-bordered"><thead><tr>
        <th>${__("Task / Month")}</th><th>${__("Allocated")}</th><th>${__("Submitted")}</th>
        <th>${__("This sheet")}</th><th>${__("Remaining")}</th></tr></thead><tbody>
        ${balances
			.map(
				(row) => `<tr><td>${escape(row.task_name || row.task)} / ${escape(row.month)}</td>
        <td>${row.allocated}</td><td>${row.submitted}</td><td>${row.current}</td>
        <td class="${row.remaining < 0 ? "text-danger" : ""}">${row.remaining}</td></tr>`
			)
			.join("")}
		</tbody></table></div>`
	);
}, 300);

frappe.ui.form.on("Timesheet", {
	refresh: refresh_allocation_balances,
	employee: refresh_allocation_balances,
	parent_project: refresh_allocation_balances,
});
frappe.ui.form.on("Timesheet Detail", {
	task(frm, cdt, cdn) {
		refresh_allocation_balances(frm);
		return append_task_to_notes(frm, cdt, cdn);
	},
	from_time: refresh_allocation_balances,
	hours: refresh_allocation_balances,
	time_logs_remove: refresh_allocation_balances,
});

async function append_task_to_notes(frm, cdt, cdn) {
	if (frm.doc.docstatus !== 0) return;
	const row = frappe.get_doc(cdt, cdn);
	const task = row?.task;
	if (!task) return;

	let label = row.custom_project_task;
	if (!label) {
		const result = await frappe.db.get_value("Task", task, "subject");
		if (frappe.get_doc(cdt, cdn)?.task !== task) return;
		label = result?.message?.subject || task;
	}

	const escaped_label = frappe.utils.escape_html(label);
	const heading = `${escaped_label}:`;
	const note = frm.doc.note || "";
	if (note.includes(heading)) return;
	await frm.set_value("note", `${note}<p>${heading} </p>`);
}

function update_row_week_of_month(frm, cdt, cdn) {
	if (frm.doc.docstatus !== 0) return;
	const row = frappe.get_doc(cdt, cdn);
	const date = row.from_time ? moment(row.from_time) : null;
	const week = date
		? "Week " +
		  (Math.floor((date.date() - 1 + date.clone().startOf("month").isoWeekday() - 1) / 7) + 1)
		: "";
	return frappe.model.set_value(cdt, cdn, "custom_week_of_month", week);
}

frappe.ui.form.on("Timesheet Detail", {
	from_time: update_row_week_of_month,
	time_logs_add: update_row_week_of_month,
});


function daily_times_input(frm) {
	return JSON.stringify({
		employee: frm.doc.employee,
		time_logs: (frm.doc.time_logs || []).map((row) => ({
			name: row.name, from_time: row.from_time, hours: row.hours,
		})),
	});
}

async function preview_daily_times(frm) {
	if (frm.doc.docstatus !== 0 || !frm.doc.employee || frm._updating_daily_times) return;
	const input = daily_times_input(frm);
	if (frm._daily_times_input === input) return;
	frm._daily_times_input = input;
	const request = (frm._daily_times_request || 0) + 1;
	frm._daily_times_request = request;
	let schedule;
	try {
		schedule = await frappe.xcall("opero.api.timesheet.preview_daily_times", {
			...JSON.parse(input), timesheet_name: frm.is_new?.() ? null : frm.doc.name,
		});
	} catch (error) {
		if (request === frm._daily_times_request) frm._daily_times_input = null;
		return; // Frappe displays the server validation message.
	}
	if (request !== frm._daily_times_request || daily_times_input(frm) !== input) return;
	frm._updating_daily_times = true;
	try {
		for (const generated of schedule) {
			const row = frm.doc.time_logs.find((entry) => entry.name === generated.name);
			if (!row) continue;
			await frappe.model.set_value(row.doctype, row.name, "from_time", generated.from_time);
			await frappe.model.set_value(row.doctype, row.name, "to_time", generated.to_time);
		}
		frm.refresh_field("time_logs");
		frm._daily_times_input = daily_times_input(frm);
	} finally {
		frm._updating_daily_times = false;
	}
}

const schedule_daily_times = frappe.utils.debounce(preview_daily_times, 250);
frappe.ui.form.on("Timesheet Detail", {
	from_time: (frm) => { if (!frm._updating_daily_times) schedule_daily_times(frm); },
	hours: (frm) => { if (!frm._updating_daily_times) schedule_daily_times(frm); },
	time_logs_remove: (frm) => schedule_daily_times(frm),
});
frappe.ui.form.on("Timesheet", {
	employee: (frm) => schedule_daily_times(frm),
});


function set_personnel_project_query(frm) {
	frm.set_query("parent_project", () => ({
		query: "opero.api.timesheet.get_personnel_projects",
		filters: { employee: frm.doc.employee, customer: frm.doc.customer },
	}));
}
frappe.ui.form.on("Timesheet", {
	setup: set_personnel_project_query,
	refresh: set_personnel_project_query,
	employee: set_personnel_project_query,
});
