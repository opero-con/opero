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
				const existing = {};
				(frm.doc.personnel_mapping || []).forEach(row => {
					existing[row.zoho_user_id] = row.personnel_id;
				});
				frm.clear_table("personnel_mapping");
				r.message.forEach(u => {
					frm.add_child("personnel_mapping", {
						zoho_user_id: u.user_id,
						zoho_user_name: u.name,
						personnel_id: existing[u.user_id] || "",
					});
				});
				frm.refresh_field("personnel_mapping");
				frappe.show_alert({ message: `${r.message.length} users loaded. Fill in the Personnel ID column and save.`, indicator: "blue" });
			},
		});
	},

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
				const existing = {};
				(frm.doc.project_mapping || []).forEach(row => {
					existing[row.zoho_project_id] = row.erpnext_project;
				});
				frm.clear_table("project_mapping");
				r.message.forEach(p => {
					frm.add_child("project_mapping", {
						zoho_project_id: p.project_id,
						zoho_project_name: p.project_name,
						erpnext_project: existing[p.project_id] || "",
					});
				});
				frm.refresh_field("project_mapping");
				frappe.show_alert({ message: `${r.message.length} projects loaded. Fill in the Cubenet Project column and save.`, indicator: "blue" });
			},
		});
	},

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

	// Build a name→id lookup for auto-matching
	const zoho_by_name = {};
	zoho_tasks.forEach(t => { zoho_by_name[t.task_name.trim().toLowerCase()] = t.task_id; });

	let auto_matched = 0;
	let rows = cubenet_tasks.map(t => {
		const task_label = t.subject || t.name;
		// Use stored ID, or auto-match by name, or empty
		let selected_id = t.zoho_task_id || zoho_by_name[task_label.trim().toLowerCase()] || "";
		if (!t.zoho_task_id && selected_id) auto_matched++;

		const is_mapped = !!selected_id;
		const row_style = is_mapped ? "background:#f0fff4;" : "";
		const badge = is_mapped
			? `<span style="color:#28a745;font-size:11px;margin-left:6px;">✓ mapped</span>`
			: `<span style="color:#999;font-size:11px;margin-left:6px;">unmapped</span>`;

		const options = `<option value="">-- Select Zoho Task --</option>` +
			zoho_tasks.map(zt =>
				`<option value="${zt.task_id}" ${zt.task_id === selected_id ? "selected" : ""}>${zt.task_name}</option>`
			).join("");

		return `
			<tr style="${row_style}">
				<td style="padding:8px 10px;vertical-align:middle;">
					${task_label}${badge}
				</td>
				<td style="padding:6px 8px;">
					<select class="form-control form-control-sm" data-task="${t.name}">
						${options}
					</select>
				</td>
			</tr>`;
	}).join("");

	const summary = auto_matched > 0
		? `<p style="color:#28a745;margin-bottom:8px;">✓ ${auto_matched} task(s) auto-matched by name. Review and save.</p>`
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
					// Refresh badges
					wrapper.find("select[data-task]").each(function () {
						const row = $(this).closest("tr");
						if ($(this).val()) {
							row.css("background", "#f0fff4");
						}
					});
				}
			},
		});
	});
}
