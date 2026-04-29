frappe.ui.form.on("Zoho Books Settings", {
	refresh(frm) {
		// Auto-render mapped sections on every page load without requiring a Fetch
		frappe.call({
			method: "opero.zoho_books.get_personnel_mappings",
			callback(r) {
				if (r.message && r.message.length) {
					render_mapped_section(
						frm.get_field("personnel_mapping_html").$wrapper,
						r.message, "personnel"
					);
				}
			},
		});
		frappe.call({
			method: "opero.zoho_books.get_project_mappings",
			callback(r) {
				const mappings = r.message || [];
				if (mappings.length) {
					render_mapped_section(
						frm.get_field("project_mapping_html").$wrapper,
						mappings, "project"
					);
				}
				// Restrict task_mapping_project to mapped projects only
				const mapped_names = mappings.map(m => m.local_name);
				frm.set_query("task_mapping_project", () => ({
					filters: mapped_names.length
						? [["name", "in", mapped_names]]
						: [["name", "=", "__none__"]],
				}));
			},
		});
	},

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
				const all_zoho_users = r.message;
				frappe.call({
					method: "opero.zoho_books.get_personnel_mappings",
					callback(mr) {
						const mapped_ids = new Set((mr.message || []).map(m => m.remote_id));
						const unmapped_zoho = all_zoho_users.filter(u => !mapped_ids.has(u.user_id));
						frappe.call({
							method: "opero.zoho_books.get_unmapped_employees",
							callback(er) {
								render_personnel_mapping(frm, unmapped_zoho, er.message || [], mr.message || []);
							},
						});
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
				const all_zoho_projects = r.message;
				frappe.call({
					method: "opero.zoho_books.get_project_mappings",
					callback(mr) {
						const mapped_ids = new Set((mr.message || []).map(m => m.remote_id));
						const unmapped_zoho = all_zoho_projects.filter(p => !mapped_ids.has(p.project_id));
						frappe.call({
							method: "opero.zoho_books.get_unmapped_projects",
							callback(pr) {
								render_project_mapping(frm, unmapped_zoho, pr.message || [], mr.message || []);
							},
						});
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
				render_task_mapping(frm, r.message);
			},
		});
	},
});


function render_personnel_mapping(frm, unmapped_zoho_users, cubenet_employees, existing_mappings) {
	const wrapper = frm.get_field("personnel_mapping_html").$wrapper;
	existing_mappings = existing_mappings || [];

	const rows = unmapped_zoho_users.map(u => `
		<tr>
			<td style="padding:8px 10px;vertical-align:middle;">${frappe.utils.escape_html(u.name)}</td>
			<td style="padding:6px 8px;position:relative;">
				<div style="display:flex;align-items:center;gap:6px;">
					<div style="flex:1;position:relative;">
						<input type="text" class="form-control form-control-sm personnel-search"
							data-remote-id="${u.user_id}"
							data-remote-name="${frappe.utils.escape_html(u.name)}"
							placeholder="Search personnel..." autocomplete="off">
						<input type="hidden" class="personnel-id">
						<div class="personnel-dropdown" style="display:none;position:absolute;z-index:1000;
							background:var(--card-bg, #fff);
							border:1px solid var(--border-color, #d1d8dd);
							border-radius:var(--border-radius, 6px);
							width:100%;
							max-height:220px;overflow-y:auto;
							box-shadow:var(--shadow-md, 0 4px 12px rgba(0,0,0,0.12));
							margin-top:2px;"></div>
					</div>
					<button class="btn btn-xs btn-success personnel-map-btn" style="display:none;white-space:nowrap;">Map</button>
				</div>
			</td>
		</tr>`
	).join("");

	const unmapped_section = unmapped_zoho_users.length ? `
		<p style="color:var(--text-muted);margin-bottom:8px;">${unmapped_zoho_users.length} unmapped Zoho user(s). Search and select a Cubenet personnel to map each row.</p>
		<table class="table table-bordered table-sm" style="margin-top:4px;">
			<thead style="background:var(--bg-light-gray, #f8f8f8);">
				<tr>
					<th style="width:40%;padding:8px 10px;">Zoho User</th>
					<th style="width:60%;padding:8px 10px;">Personnel (Cubenet)</th>
				</tr>
				<tr style="background:var(--bg-light-gray, #f8f8f8);">
					<td style="padding:4px 6px;">
						<input type="text" class="zoho-row-filter" autocomplete="off"
							placeholder="Filter..."
							style="width:100%;padding:3px 8px;border:1px solid var(--border-color, #d1d8dd);
								border-radius:var(--border-radius, 4px);font-size:var(--text-sm, 12px);
								background:var(--control-bg, #f5f7fa);color:var(--text-color, #333);outline:none;">
					</td>
					<td></td>
				</tr>
			</thead>
			<tbody>${rows}</tbody>
		</table>` : `<p class="text-muted" style="margin-bottom:12px;">All Zoho users are mapped.</p>`;

	const mapped_rows = existing_mappings.map(m => `
		<tr>
			<td style="padding:8px 10px;vertical-align:middle;">${frappe.utils.escape_html(m.remote_name || m.remote_id)}</td>
			<td style="padding:8px 10px;vertical-align:middle;">${frappe.utils.escape_html(m.local_name)}</td>
			<td style="padding:6px 8px;text-align:right;">
				<button class="btn btn-xs btn-danger unmap-btn" data-mapping-name="${frappe.utils.escape_html(m.name)}" style="font-size:11px;">
					Unmap
				</button>
			</td>
		</tr>`
	).join("");

	wrapper.html(unmapped_section);
	render_mapped_section(wrapper, existing_mappings, "personnel");

	wrapper.find(".zoho-row-filter").on("input", function () {
		const q = $(this).val().trim().toLowerCase();
		wrapper.find("tbody tr").each(function () {
			const name = $(this).find("td:first").text().trim().toLowerCase();
			$(this).toggle(!q || name.includes(q));
		});
	});

	const pending_selections = new Set();

	function show_dropdown($input, $dropdown, query) {
		const own_id = $input.siblings(".personnel-id").val();
		const matches = cubenet_employees.filter(e =>
			(e.name === own_id || !pending_selections.has(e.name)) &&
			(!query || e.employee_name.toLowerCase().includes(query) || e.name.toLowerCase().includes(query))
		).slice(0, 20);

		if (!matches.length) { $dropdown.hide(); return; }

		$dropdown.html(matches.map(e => `
			<div class="personnel-option" data-id="${frappe.utils.escape_html(e.name)}"
				data-label="${frappe.utils.escape_html(e.employee_name)}"
				style="padding:var(--padding-sm, 6px) var(--padding-md, 12px);
					cursor:pointer;
					font-size:var(--text-sm, 13px);
					color:var(--text-color, #333);
					border-bottom:1px solid var(--border-color, #f0f0f0);">
				${frappe.utils.escape_html(e.employee_name)}
				<span style="color:var(--text-muted, #8d99a6);font-size:var(--text-xs, 11px);margin-left:6px;">${frappe.utils.escape_html(e.name)}</span>
			</div>`
		).join("")).show();
	}

	wrapper.find(".personnel-search").each(function () {
		const $input = $(this);
		const $hidden = $input.siblings(".personnel-id");
		const $dropdown = $input.siblings(".personnel-dropdown");

		$input.on("focus click", function () {
			show_dropdown($input, $dropdown, $(this).val().trim().toLowerCase());
		});

		$input.on("input", function () {
			$hidden.val("");
			show_dropdown($input, $dropdown, $(this).val().trim().toLowerCase());
		});

		$dropdown.on("mouseover", ".personnel-option", function () {
			$(this).css("background", "var(--fg-hover-color, #f5f7fa)");
		}).on("mouseout", ".personnel-option", function () {
			$(this).css("background", "");
		}).on("mousedown", ".personnel-option", function () {
			const prev_id = $hidden.val();
			if (prev_id) pending_selections.delete(prev_id);
			const new_id = $(this).data("id");
			$input.val($(this).data("label"));
			$hidden.val(new_id);
			pending_selections.add(new_id);
			$dropdown.hide();
			$input.closest("div").siblings(".personnel-map-btn").show();
		});

		$input.on("blur", function () {
			setTimeout(() => $dropdown.hide(), 150);
		});

		$input.on("input", function () {
			if (!$(this).val().trim()) {
				const prev_id = $hidden.val();
				if (prev_id) pending_selections.delete(prev_id);
				$hidden.val("");
				$input.closest("div").siblings(".personnel-map-btn").hide();
			}
		});
	});

	wrapper.find(".personnel-map-btn").on("click", function () {
		const $btn = $(this);
		const $row = $btn.closest("tr");
		const $input = $row.find(".personnel-search");
		const local_name = $row.find(".personnel-id").val() || $input.val().trim();
		if (!local_name) return;

		frappe.call({
			method: "opero.zoho_books.save_personnel_mappings",
			args: { mappings: JSON.stringify([{
				local_name,
				remote_id: $input.data("remote-id"),
				remote_name: $input.data("remote-name"),
			}]) },
			callback(r) {
				if (r.message && r.message.saved && r.message.saved.length) {
					const m = r.message.saved[0];
					$row.fadeOut(200, () => {
						$row.remove();
						const $tbody = wrapper.find(".mapped-personnel-tbody");
						const new_row = `<tr>
							<td style="padding:8px 10px;vertical-align:middle;">${frappe.utils.escape_html(m.remote_name || m.remote_id)}</td>
							<td style="padding:8px 10px;vertical-align:middle;">${frappe.utils.escape_html(m.local_name)}</td>
							<td style="padding:6px 8px;text-align:right;">
								<button class="btn btn-xs btn-danger unmap-btn" data-mapping-name="${frappe.utils.escape_html(m.name)}" style="font-size:11px;">Unmap</button>
							</td>
						</tr>`;
						if ($tbody.length) {
							$tbody.append(new_row);
							wrapper.find(".mapped-count").text(parseInt(wrapper.find(".mapped-count").text() || 0) + 1);
						} else {
							wrapper.append(`
								<hr style="margin:16px 0 12px;">
								<p style="font-weight:600;margin-bottom:8px;">Mapped (<span class="mapped-count">1</span>)</p>
								<table class="table table-bordered table-sm">
									<thead style="background:var(--bg-light-gray, #f8f8f8);">
										<tr>
											<th style="width:40%;padding:8px 10px;">Zoho User</th>
											<th style="width:45%;padding:8px 10px;">Personnel (Cubenet)</th>
											<th style="width:15%;padding:8px 10px;"></th>
										</tr>
									</thead>
									<tbody class="mapped-personnel-tbody">${new_row}</tbody>
								</table>`);
						}
						render_mapped_section(wrapper, [m], "personnel");
						frappe.show_alert({ message: "Mapped successfully.", indicator: "green" });
					});
				}
			},
		});
	});
}


function render_project_mapping(frm, unmapped_zoho_projects, cubenet_projects, existing_mappings) {
	const wrapper = frm.get_field("project_mapping_html").$wrapper;
	existing_mappings = existing_mappings || [];

	const rows = unmapped_zoho_projects.map(p => `
		<tr>
			<td style="padding:8px 10px;vertical-align:middle;">${frappe.utils.escape_html(p.project_name)}</td>
			<td style="padding:6px 8px;position:relative;">
				<div style="display:flex;align-items:center;gap:6px;">
					<div style="flex:1;position:relative;">
						<input type="text" class="form-control form-control-sm project-search"
							data-remote-id="${p.project_id}"
							data-remote-name="${frappe.utils.escape_html(p.project_name)}"
							placeholder="Search project..." autocomplete="off">
						<input type="hidden" class="project-id">
						<div class="project-dropdown" style="display:none;position:absolute;z-index:1000;
							background:var(--card-bg, #fff);
							border:1px solid var(--border-color, #d1d8dd);
							border-radius:var(--border-radius, 6px);
							width:100%;
							max-height:220px;overflow-y:auto;
							box-shadow:var(--shadow-md, 0 4px 12px rgba(0,0,0,0.12));
							margin-top:2px;"></div>
					</div>
					<button class="btn btn-xs btn-success project-map-btn" style="display:none;white-space:nowrap;">Map</button>
				</div>
			</td>
		</tr>`
	).join("");

	const unmapped_section = unmapped_zoho_projects.length ? `
		<p style="color:var(--text-muted);margin-bottom:8px;">${unmapped_zoho_projects.length} unmapped Zoho project(s). Search and select a Cubenet project to map each row.</p>
		<table class="table table-bordered table-sm" style="margin-top:4px;">
			<thead style="background:var(--bg-light-gray, #f8f8f8);">
				<tr>
					<th style="width:40%;padding:8px 10px;">Zoho Project</th>
					<th style="width:60%;padding:8px 10px;">Project (Cubenet)</th>
				</tr>
				<tr style="background:var(--bg-light-gray, #f8f8f8);">
					<td style="padding:4px 6px;">
						<input type="text" class="zoho-row-filter" autocomplete="off"
							placeholder="Filter..."
							style="width:100%;padding:3px 8px;border:1px solid var(--border-color, #d1d8dd);
								border-radius:var(--border-radius, 4px);font-size:var(--text-sm, 12px);
								background:var(--control-bg, #f5f7fa);color:var(--text-color, #333);outline:none;">
					</td>
					<td></td>
				</tr>
			</thead>
			<tbody>${rows}</tbody>
		</table>` : `<p class="text-muted" style="margin-bottom:12px;">All Zoho projects are mapped.</p>`;

	wrapper.html(unmapped_section);
	render_mapped_section(wrapper, existing_mappings, "project");

	wrapper.find(".zoho-row-filter").on("input", function () {
		const q = $(this).val().trim().toLowerCase();
		wrapper.find("tbody tr").each(function () {
			const name = $(this).find("td:first").text().trim().toLowerCase();
			$(this).toggle(!q || name.includes(q));
		});
	});

	const pending_project_selections = new Set();

	function show_dropdown($input, $dropdown, query) {
		const own_id = $input.siblings(".project-id").val();
		const matches = cubenet_projects.filter(p =>
			(p.name === own_id || !pending_project_selections.has(p.name)) &&
			(!query || (p.project_name || "").toLowerCase().includes(query) || p.name.toLowerCase().includes(query))
		).slice(0, 20);

		if (!matches.length) { $dropdown.hide(); return; }

		$dropdown.html(matches.map(p => `
			<div class="project-option" data-id="${frappe.utils.escape_html(p.name)}"
				data-label="${frappe.utils.escape_html(p.project_name || p.name)}"
				style="padding:var(--padding-sm, 6px) var(--padding-md, 12px);
					cursor:pointer;
					font-size:var(--text-sm, 13px);
					color:var(--text-color, #333);
					border-bottom:1px solid var(--border-color, #f0f0f0);">
				${frappe.utils.escape_html(p.project_name || p.name)}
				<span style="color:var(--text-muted, #8d99a6);font-size:var(--text-xs, 11px);margin-left:6px;">${frappe.utils.escape_html(p.name)}</span>
			</div>`
		).join("")).show();
	}

	wrapper.find(".project-search").each(function () {
		const $input = $(this);
		const $hidden = $input.siblings(".project-id");
		const $dropdown = $input.siblings(".project-dropdown");

		$input.on("focus click", function () {
			show_dropdown($input, $dropdown, $(this).val().trim().toLowerCase());
		});
		$input.on("input", function () {
			$hidden.val("");
			show_dropdown($input, $dropdown, $(this).val().trim().toLowerCase());
		});
		$dropdown.on("mouseover", ".project-option", function () {
			$(this).css("background", "var(--fg-hover-color, #f5f7fa)");
		}).on("mouseout", ".project-option", function () {
			$(this).css("background", "");
		}).on("mousedown", ".project-option", function () {
			const prev_id = $hidden.val();
			if (prev_id) pending_project_selections.delete(prev_id);
			const new_id = $(this).data("id");
			$input.val($(this).data("label"));
			$hidden.val(new_id);
			pending_project_selections.add(new_id);
			$dropdown.hide();
			$input.closest("div").siblings(".project-map-btn").show();
		});
		$input.on("blur", function () {
			setTimeout(() => $dropdown.hide(), 150);
		});
		$input.on("input", function () {
			if (!$(this).val().trim()) {
				const prev_id = $hidden.val();
				if (prev_id) pending_project_selections.delete(prev_id);
				$hidden.val("");
				$input.closest("div").siblings(".project-map-btn").hide();
			}
		});
	});

	wrapper.find(".project-map-btn").on("click", function () {
		const $btn = $(this);
		const $row = $btn.closest("tr");
		const $input = $row.find(".project-search");
		const local_name = $row.find(".project-id").val() || $input.val().trim();
		if (!local_name) return;

		frappe.call({
			method: "opero.zoho_books.save_project_mappings",
			args: { mappings: JSON.stringify([{
				local_name,
				remote_id: $input.data("remote-id"),
				remote_name: $input.data("remote-name"),
			}]) },
			callback(r) {
				if (r.message && r.message.saved && r.message.saved.length) {
					const m = r.message.saved[0];
					$row.fadeOut(200, () => {
						$row.remove();
						const $tbody = wrapper.find(".mapped-project-tbody");
						const new_row = `<tr>
							<td style="padding:8px 10px;vertical-align:middle;">${frappe.utils.escape_html(m.remote_name || m.remote_id)}</td>
							<td style="padding:8px 10px;vertical-align:middle;">${frappe.utils.escape_html(m.local_name)}</td>
							<td style="padding:6px 8px;text-align:right;">
								<button class="btn btn-xs btn-danger unmap-project-btn" data-mapping-name="${frappe.utils.escape_html(m.name)}" style="font-size:11px;">Unmap</button>
							</td>
						</tr>`;
						if ($tbody.length) {
							$tbody.append(new_row);
							wrapper.find(".mapped-count").text(parseInt(wrapper.find(".mapped-count").text() || 0) + 1);
						} else {
							wrapper.append(`
								<hr style="margin:16px 0 12px;">
								<p style="font-weight:600;margin-bottom:8px;">Mapped (<span class="mapped-count">1</span>)</p>
								<table class="table table-bordered table-sm">
									<thead style="background:var(--bg-light-gray, #f8f8f8);">
										<tr>
											<th style="width:40%;padding:8px 10px;">Zoho Project</th>
											<th style="width:45%;padding:8px 10px;">Project (Cubenet)</th>
											<th style="width:15%;padding:8px 10px;"></th>
										</tr>
									</thead>
									<tbody class="mapped-project-tbody">${new_row}</tbody>
								</table>`);
						}
						render_mapped_section(wrapper, [m], "project");
						frappe.show_alert({ message: "Mapped successfully.", indicator: "green" });
					});
				}
			},
		});
	});
}


function render_task_mapping(frm, data) {
	const wrapper = frm.get_field("task_mapping_html").$wrapper;
	wrapper.empty();

	const { unmapped_zoho_tasks, unmapped_cubenet_tasks, existing_mappings } = data;

	if (!unmapped_cubenet_tasks.length && !unmapped_zoho_tasks.length && !existing_mappings.length) {
		wrapper.html(`<p class="text-muted">No tasks found for this project in Cubenet.</p>`);
		return;
	}

	// When Zoho has no tasks yet, show Cubenet tasks so user knows what exists
	if (!unmapped_zoho_tasks.length) {
		const cubenet_rows = unmapped_cubenet_tasks.map(t => `
			<tr>
				<td style="padding:8px 10px;vertical-align:middle;">${frappe.utils.escape_html(t.subject || t.name)}</td>
				<td style="padding:8px 10px;vertical-align:middle;color:var(--text-muted);">
					<span style="font-size:12px;">Will be auto-created in Zoho on first sync</span>
				</td>
			</tr>`
		).join("");

		const no_zoho_section = unmapped_cubenet_tasks.length ? `
			<p style="color:var(--text-muted);margin-bottom:8px;">No tasks in Zoho yet. The following Cubenet tasks will be auto-created in Zoho on first timesheet sync.</p>
			<table class="table table-bordered table-sm" style="margin-top:4px;">
				<thead style="background:var(--bg-light-gray,#f8f8f8);">
					<tr>
						<th style="width:45%;padding:8px 10px;">Task (Cubenet)</th>
						<th style="width:55%;padding:8px 10px;">Zoho Status</th>
					</tr>
				</thead>
				<tbody>${cubenet_rows}</tbody>
			</table>` : "";

		wrapper.html(no_zoho_section);
		render_mapped_section(wrapper, existing_mappings, "task");
		return;
	}

	const rows = unmapped_zoho_tasks.map(t => `
		<tr>
			<td style="padding:8px 10px;vertical-align:middle;">${frappe.utils.escape_html(t.task_name)}</td>
			<td style="padding:6px 8px;position:relative;">
				<div style="display:flex;align-items:center;gap:6px;">
					<div style="flex:1;position:relative;">
						<input type="text" class="form-control form-control-sm task-search"
							data-remote-id="${t.task_id}"
							data-remote-name="${frappe.utils.escape_html(t.task_name)}"
							placeholder="Search task..." autocomplete="off">
						<input type="hidden" class="task-id">
						<div class="task-dropdown" style="display:none;position:absolute;z-index:1000;
							background:var(--card-bg,#fff);border:1px solid var(--border-color,#d1d8dd);
							border-radius:var(--border-radius,6px);width:100%;max-height:220px;overflow-y:auto;
							box-shadow:var(--shadow-md,0 4px 12px rgba(0,0,0,.12));margin-top:2px;"></div>
					</div>
					<button class="btn btn-xs btn-success task-map-btn" style="display:none;white-space:nowrap;">Map</button>
				</div>
			</td>
		</tr>`
	).join("");

	const unmapped_section = `
		<p style="color:var(--text-muted);margin-bottom:8px;">${unmapped_zoho_tasks.length} unmapped Zoho task(s). Search and select a Cubenet task to map each row.</p>
		<table class="table table-bordered table-sm" style="margin-top:4px;">
			<thead style="background:var(--bg-light-gray,#f8f8f8);">
				<tr>
					<th style="width:40%;padding:8px 10px;">Zoho Task</th>
					<th style="width:60%;padding:8px 10px;">Task (Cubenet)</th>
				</tr>
				<tr style="background:var(--bg-light-gray,#f8f8f8);">
					<td style="padding:4px 6px;">
						<input type="text" class="zoho-row-filter" autocomplete="off" placeholder="Filter..."
							style="width:100%;padding:3px 8px;border:1px solid var(--border-color,#d1d8dd);
							border-radius:var(--border-radius,4px);font-size:var(--text-sm,12px);
							background:var(--control-bg,#f5f7fa);color:var(--text-color,#333);outline:none;">
					</td>
					<td></td>
				</tr>
			</thead>
			<tbody>${rows}</tbody>
		</table>`;

	wrapper.html(unmapped_section);
	render_mapped_section(wrapper, existing_mappings, "task");

	wrapper.find(".zoho-row-filter").on("input", function () {
		const q = $(this).val().trim().toLowerCase();
		wrapper.find("tbody tr").each(function () {
			$(this).toggle(!q || $(this).find("td:first").text().trim().toLowerCase().includes(q));
		});
	});

	const pending_task_selections = new Set();

	function show_task_dropdown($input, $dropdown, query) {
		const own_id = $input.siblings(".task-id").val();
		const matches = unmapped_cubenet_tasks.filter(t =>
			(t.name === own_id || !pending_task_selections.has(t.name)) &&
			(!query || (t.subject || t.name).toLowerCase().includes(query) || t.name.toLowerCase().includes(query))
		).slice(0, 20);

		if (!matches.length) { $dropdown.hide(); return; }

		$dropdown.html(matches.map(t => `
			<div class="task-option" data-id="${frappe.utils.escape_html(t.name)}"
				data-label="${frappe.utils.escape_html(t.subject || t.name)}"
				style="padding:var(--padding-sm,6px) var(--padding-md,12px);cursor:pointer;
					font-size:var(--text-sm,13px);color:var(--text-color,#333);
					border-bottom:1px solid var(--border-color,#f0f0f0);">
				${frappe.utils.escape_html(t.subject || t.name)}
				<span style="color:var(--text-muted,#8d99a6);font-size:var(--text-xs,11px);margin-left:6px;">${frappe.utils.escape_html(t.name)}</span>
			</div>`
		).join("")).show();
	}

	wrapper.find(".task-search").each(function () {
		const $input = $(this);
		const $hidden = $input.siblings(".task-id");
		const $dropdown = $input.siblings(".task-dropdown");

		$input.on("focus click", function () {
			show_task_dropdown($input, $dropdown, $(this).val().trim().toLowerCase());
		});
		$input.on("input", function () {
			$hidden.val("");
			if (!$(this).val().trim()) {
				const prev = $hidden.val();
				if (prev) pending_task_selections.delete(prev);
				$input.closest("div").siblings(".task-map-btn").hide();
			}
			show_task_dropdown($input, $dropdown, $(this).val().trim().toLowerCase());
		});
		$dropdown.on("mouseover", ".task-option", function () {
			$(this).css("background", "var(--fg-hover-color,#f5f7fa)");
		}).on("mouseout", ".task-option", function () {
			$(this).css("background", "");
		}).on("mousedown", ".task-option", function () {
			const prev = $hidden.val();
			if (prev) pending_task_selections.delete(prev);
			const new_id = $(this).data("id");
			$input.val($(this).data("label"));
			$hidden.val(new_id);
			pending_task_selections.add(new_id);
			$dropdown.hide();
			$input.closest("div").siblings(".task-map-btn").show();
		});
		$input.on("blur", function () {
			setTimeout(() => $dropdown.hide(), 150);
		});
	});

	wrapper.find(".task-map-btn").on("click", function () {
		const $btn = $(this);
		const $row = $btn.closest("tr");
		const $input = $row.find(".task-search");
		const local_name = $row.find(".task-id").val() || $input.val().trim();
		if (!local_name) return;

		frappe.call({
			method: "opero.zoho_books.save_task_mappings",
			args: { mappings: JSON.stringify([{
				local_name,
				remote_id: $input.data("remote-id"),
				remote_name: $input.data("remote-name"),
			}]) },
			callback(r) {
				if (r.message && r.message.saved && r.message.saved.length) {
					const m = r.message.saved[0];
					$row.fadeOut(200, () => {
						$row.remove();
						render_mapped_section(wrapper, [m], "task");
						frappe.show_alert({ message: "Task mapped successfully.", indicator: "green" });
					});
				}
			},
		});
	});
}


function render_mapped_section(wrapper, mappings, type) {
	if (!mappings || !mappings.length) return;

	const is_personnel = type === "personnel";
	const is_task = type === "task";
	const tbody_class = is_personnel ? "mapped-personnel-tbody" : is_task ? "mapped-task-tbody" : "mapped-project-tbody";
	const unmap_class = is_personnel ? "unmap-btn" : is_task ? "unmap-task-btn" : "unmap-project-btn";
	const delete_method = is_personnel
		? "opero.zoho_books.delete_personnel_mapping"
		: is_task
			? "opero.zoho_books.delete_task_mapping"
			: "opero.zoho_books.delete_project_mapping";
	const label_a = is_personnel ? "Zoho User" : is_task ? "Zoho Task" : "Zoho Project";
	const label_b = is_personnel ? "Personnel (Cubenet)" : is_task ? "Task (Cubenet)" : "Project (Cubenet)";

	const rows = mappings.map(m => `
		<tr>
			<td style="padding:8px 10px;vertical-align:middle;">${frappe.utils.escape_html(m.remote_name || m.remote_id)}</td>
			<td style="padding:8px 10px;vertical-align:middle;">${frappe.utils.escape_html(m.local_name)}</td>
			<td style="padding:6px 8px;text-align:right;">
				<button class="btn btn-xs btn-danger ${unmap_class}"
					data-mapping-name="${frappe.utils.escape_html(m.name)}" style="font-size:11px;">Unmap</button>
			</td>
		</tr>`
	).join("");

	wrapper.append(`
		<hr style="margin:16px 0 12px;">
		<p style="font-weight:600;margin-bottom:8px;">Mapped (<span class="mapped-count">${mappings.length}</span>)</p>
		<table class="table table-bordered table-sm">
			<thead style="background:var(--bg-light-gray, #f8f8f8);">
				<tr>
					<th style="width:40%;padding:8px 10px;">${label_a}</th>
					<th style="width:45%;padding:8px 10px;">${label_b}</th>
					<th style="width:15%;padding:8px 10px;"></th>
				</tr>
			</thead>
			<tbody class="${tbody_class}">${rows}</tbody>
		</table>`);

	wrapper.find(`.${unmap_class}`).off("click").on("click", function () {
		const mapping_name = $(this).data("mapping-name");
		const $row = $(this).closest("tr");
		frappe.confirm("Remove this mapping?", () => {
			frappe.call({
				method: delete_method,
				args: { mapping_name },
				callback(r) {
					if (r.message) {
						$row.fadeOut(200, () => $row.remove());
						frappe.show_alert({ message: "Mapping removed.", indicator: "orange" });
					}
				},
			});
		});
	});
}
