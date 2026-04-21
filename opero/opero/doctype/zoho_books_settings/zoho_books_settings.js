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

	const zoho_options = zoho_tasks.map(t =>
		`<option value="${t.task_id}">${t.task_name}</option>`
	).join("");

	let rows = cubenet_tasks.map(t => {
		const selected_id = t.zoho_task_id || "";
		const options = `<option value="">-- Not Mapped --</option>` +
			zoho_tasks.map(zt =>
				`<option value="${zt.task_id}" ${zt.task_id === selected_id ? "selected" : ""}>${zt.task_name}</option>`
			).join("");
		return `
			<tr>
				<td style="padding:6px 8px;">${t.subject || t.name}</td>
				<td style="padding:6px 8px;">
					<select class="form-control form-control-sm" data-task="${t.name}">
						${options}
					</select>
				</td>
			</tr>`;
	}).join("");

	wrapper.html(`
		<table class="table table-bordered table-sm" style="margin-top:10px;">
			<thead>
				<tr>
					<th style="width:50%">Cubenet Task</th>
					<th style="width:50%">Zoho Task</th>
				</tr>
			</thead>
			<tbody>${rows}</tbody>
		</table>
		<button class="btn btn-primary btn-sm" id="save_task_mappings" style="margin-top:8px;">
			Save Task Mappings
		</button>
		<span id="task_mapping_status" style="margin-left:10px;"></span>
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
					frappe.show_alert({ message: `${r.message.count} task(s) mapped successfully.`, indicator: "green" });
				}
			},
		});
	});
}
