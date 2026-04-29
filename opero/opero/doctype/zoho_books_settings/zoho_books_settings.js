frappe.ui.form.on("Zoho Books Settings", {
	connect_button(frm) {
		frm.save().then(() => {
			frappe.call({
				method: "opero.zoho_books.get_authorization_url",
				callback(r) {
					if (r.message) window.open(r.message, "_blank");
				},
			});
		});
	},

	// Personnel Mapping tab
	fetch_users_button(frm) {
		frappe.call({
			method: "opero.zoho_books.get_zoho_users",
			freeze: true,
			freeze_message: "Fetching users from Zoho Books...",
			callback(r) {
				if (!r.message || !r.message.length) {
					frappe.msgprint("No users found in Zoho Books.");
					return;
				}
				frappe.call({
					method: "opero.zoho_books.get_personnel_mappings",
					callback(mr) {
						render_personnel_mapping(frm, r.message, mr.message || []);
					},
				});
			},
		});
	},

	// Project Mapping tab
	fetch_projects_button(frm) {
		frappe.call({
			method: "opero.zoho_books.get_zoho_projects",
			freeze: true,
			freeze_message: "Fetching projects from Zoho Books...",
			callback(r) {
				if (!r.message || !r.message.length) {
					frappe.msgprint("No projects found in Zoho Books.");
					return;
				}
				frappe.call({
					method: "opero.zoho_books.get_project_mappings",
					callback(mr) {
						render_project_mapping(frm, r.message, mr.message || []);
					},
				});
			},
		});
	},

	// Task Mapping tab
	load_tasks_button(frm) {
		const project = frm.doc.task_mapping_project;
		if (!project) {
			frappe.msgprint("Select a project first.");
			return;
		}
		frappe.call({
			method: "opero.zoho_books.get_task_mapping_data",
			args: { project },
			freeze: true,
			freeze_message: "Loading tasks...",
			callback(r) {
				if (!r.message) return;
				render_task_mapping(frm, r.message.cubenet_tasks, r.message.zoho_tasks);
			},
		});
	},
});


function render_personnel_mapping(frm, zoho_users, existing_mappings) {
	const wrapper = frm.get_field("personnel_mapping_html").$wrapper;

	// remote_id → local_name lookup from existing mappings
	const mapped = {};
	existing_mappings.forEach(m => { mapped[m.remote_id] = m.local_name; });

	const rows = zoho_users.map(u => {
		const local = mapped[u.user_id] || "";
		const is_mapped = !!local;
		const row_style = is_mapped ? "background:#f0fff4;" : "";
		const badge = is_mapped
			? `<span style="color:#28a745;font-size:11px;margin-left:6px;">&#10003; mapped</span>`
			: `<span style="color:#999;font-size:11px;margin-left:6px;">unmapped</span>`;
		return `
			<tr style="${row_style}">
				<td style="padding:8px 10px;vertical-align:middle;">${frappe.utils.escape_html(u.name)}${badge}</td>
				<td style="padding:6px 8px;">
					<input class="form-control form-control-sm" type="text"
						data-remote-id="${u.user_id}"
						data-remote-name="${frappe.utils.escape_html(u.name)}"
						placeholder="Employee name"
						value="${frappe.utils.escape_html(local)}">
				</td>
			</tr>`;
	}).join("");

	wrapper.html(`
		<p style="color:#666;margin-bottom:8px;">Enter the Cubenet Employee name for each Zoho user, then click Save.</p>
		<table class="table table-bordered table-sm" style="margin-top:4px;">
			<thead style="background:#f8f8f8;">
				<tr>
					<th style="width:45%;padding:8px 10px;">Zoho User</th>
					<th style="width:55%;padding:8px 10px;">Employee (Cubenet)</th>
				</tr>
			</thead>
			<tbody>${rows}</tbody>
		</table>
		<button class="btn btn-primary btn-sm" id="save_personnel_mappings" style="margin-top:8px;">
			Save Personnel Mappings
		</button>
	`);

	wrapper.find("#save_personnel_mappings").on("click", function () {
		const mappings = [];
		wrapper.find("input[data-remote-id]").each(function () {
			const local_name = $(this).val().trim();
			if (local_name) {
				mappings.push({
					local_name,
					remote_id: $(this).data("remote-id"),
					remote_name: $(this).data("remote-name"),
				});
			}
		});
		if (!mappings.length) {
			frappe.show_alert({ message: "No mappings to save.", indicator: "orange" });
			return;
		}
		frappe.call({
			method: "opero.zoho_books.save_personnel_mappings",
			args: { mappings: JSON.stringify(mappings) },
			callback(r) {
				if (r.message) {
					frappe.show_alert({ message: `${r.message.count} personnel mapping(s) saved.`, indicator: "green" });
					wrapper.find("input[data-remote-id]").each(function () {
						const row = $(this).closest("tr");
						if ($(this).val().trim()) {
							row.css("background", "#f0fff4");
						}
					});
				}
			},
		});
	});
}


function render_project_mapping(frm, zoho_projects, existing_mappings) {
	const wrapper = frm.get_field("project_mapping_html").$wrapper;

	// remote_id → local_name lookup
	const mapped = {};
	existing_mappings.forEach(m => { mapped[m.remote_id] = m.local_name; });

	const rows = zoho_projects.map(p => {
		const local = mapped[p.project_id] || "";
		const is_mapped = !!local;
		const row_style = is_mapped ? "background:#f0fff4;" : "";
		const badge = is_mapped
			? `<span style="color:#28a745;font-size:11px;margin-left:6px;">&#10003; mapped</span>`
			: `<span style="color:#999;font-size:11px;margin-left:6px;">unmapped</span>`;
		return `
			<tr style="${row_style}">
				<td style="padding:8px 10px;vertical-align:middle;">${frappe.utils.escape_html(p.project_name)}${badge}</td>
				<td style="padding:6px 8px;">
					<input class="form-control form-control-sm" type="text"
						data-remote-id="${p.project_id}"
						data-remote-name="${frappe.utils.escape_html(p.project_name)}"
						placeholder="Project name"
						value="${frappe.utils.escape_html(local)}">
				</td>
			</tr>`;
	}).join("");

	wrapper.html(`
		<p style="color:#666;margin-bottom:8px;">Enter the Cubenet Project name for each Zoho project, then click Save.</p>
		<table class="table table-bordered table-sm" style="margin-top:4px;">
			<thead style="background:#f8f8f8;">
				<tr>
					<th style="width:45%;padding:8px 10px;">Zoho Project</th>
					<th style="width:55%;padding:8px 10px;">Project (Cubenet)</th>
				</tr>
			</thead>
			<tbody>${rows}</tbody>
		</table>
		<button class="btn btn-primary btn-sm" id="save_project_mappings" style="margin-top:8px;">
			Save Project Mappings
		</button>
	`);

	wrapper.find("#save_project_mappings").on("click", function () {
		const mappings = [];
		wrapper.find("input[data-remote-id]").each(function () {
			const local_name = $(this).val().trim();
			if (local_name) {
				mappings.push({
					local_name,
					remote_id: $(this).data("remote-id"),
					remote_name: $(this).data("remote-name"),
				});
			}
		});
		if (!mappings.length) {
			frappe.show_alert({ message: "No mappings to save.", indicator: "orange" });
			return;
		}
		frappe.call({
			method: "opero.zoho_books.save_project_mappings",
			args: { mappings: JSON.stringify(mappings) },
			callback(r) {
				if (r.message) {
					frappe.show_alert({ message: `${r.message.count} project mapping(s) saved.`, indicator: "green" });
					wrapper.find("input[data-remote-id]").each(function () {
						const row = $(this).closest("tr");
						if ($(this).val().trim()) {
							row.css("background", "#f0fff4");
						}
					});
				}
			},
		});
	});
}


function render_task_mapping(frm, cubenet_tasks, zoho_tasks) {
	const wrapper = frm.get_field("task_mapping_html").$wrapper;
	wrapper.empty();

	if (!cubenet_tasks.length) {
		wrapper.html(`<p class="text-muted">No tasks found for this project in Cubenet.</p>`);
		return;
	}

	if (!zoho_tasks.length) {
		wrapper.html(`<p class="text-muted">No tasks found in Zoho for this project.</p>`);
		return;
	}

	const zoho_by_name = {};
	zoho_tasks.forEach(t => { zoho_by_name[t.task_name.trim().toLowerCase()] = t.task_id; });

	let auto_matched = 0;
	let rows = cubenet_tasks.map(t => {
		const task_label = t.subject || t.name;
		let selected_id = t.zoho_task_id || zoho_by_name[task_label.trim().toLowerCase()] || "";
		if (!t.zoho_task_id && selected_id) auto_matched++;

		const is_mapped = !!selected_id;
		const row_style = is_mapped ? "background:#f0fff4;" : "";
		const badge = is_mapped
			? `<span style="color:#28a745;font-size:11px;margin-left:6px;">&#10003; mapped</span>`
			: `<span style="color:#999;font-size:11px;margin-left:6px;">unmapped</span>`;

		const options = `<option value="">-- Select Zoho Task --</option>` +
			zoho_tasks.map(zt =>
				`<option value="${zt.task_id}" ${zt.task_id === selected_id ? "selected" : ""}>${zt.task_name}</option>`
			).join("");

		return `
			<tr style="${row_style}">
				<td style="padding:8px 10px;vertical-align:middle;">${task_label}${badge}</td>
				<td style="padding:6px 8px;">
					<select class="form-control form-control-sm" data-task="${t.name}">
						${options}
					</select>
				</td>
			</tr>`;
	}).join("");

	const summary = auto_matched > 0
		? `<p style="color:#28a745;margin-bottom:8px;">&#10003; ${auto_matched} task(s) auto-matched by name. Review and save.</p>`
		: `<p style="color:#666;margin-bottom:8px;">Select the matching Zoho task for each row, then click Save.</p>`;

	wrapper.html(`
		${summary}
		<table class="table table-bordered table-sm" style="margin-top:4px;">
			<thead style="background:#f8f8f8;">
				<tr>
					<th style="width:45%;padding:8px 10px;">Cubenet Task</th>
					<th style="width:55%;padding:8px 10px;">Zoho Task</th>
				</tr>
			</thead>
			<tbody>${rows}</tbody>
		</table>
		<button class="btn btn-primary btn-sm" id="save_task_mappings" style="margin-top:8px;">
			Save Task Mappings
		</button>
	`);

	wrapper.find("#save_task_mappings").on("click", function () {
		const mappings = [];
		wrapper.find("select[data-task]").each(function () {
			const zoho_task_id = $(this).val();
			if (zoho_task_id) {
				mappings.push({ cubenet_task: $(this).data("task"), zoho_task_id });
			}
		});
		if (!mappings.length) {
			frappe.show_alert({ message: "No mappings to save.", indicator: "orange" });
			return;
		}
		frappe.call({
			method: "opero.zoho_books.save_task_mappings",
			args: { mappings: JSON.stringify(mappings) },
			callback(r) {
				if (r.message) {
					frappe.show_alert({ message: `${r.message.count} task(s) mapped and saved.`, indicator: "green" });
					wrapper.find("select[data-task]").each(function () {
						if ($(this).val()) {
							$(this).closest("tr").css("background", "#f0fff4");
						}
					});
				}
			},
		});
	});
}
