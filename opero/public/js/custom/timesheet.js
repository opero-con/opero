// Opero: client scripts for Timesheet
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// --- Auto Height Note: TS ---
frappe.ui.form.on('Timesheet', {
    onload: function(frm) {
        // Inject dynamic CSS if not already present
        if (!document.getElementById('resize-note-css')) {
            const style = document.createElement('style');
            style.id = 'resize-note-css';
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
            const editor = frm.fields_dict.note?.$wrapper.find('.ql-editor')[0];
            if (editor) {
                const lineHeight = 22; // Approx line height in pixels
                const extraPadding = lineHeight * 2;

                editor.style.height = 'auto';
                editor.style.height = (editor.scrollHeight + extraPadding) + 'px';
            }
        }

        setTimeout(resizeNoteEditor, 500); // Initial resize
        frm.fields_dict.note?.$wrapper.find('.ql-editor').on('input', resizeNoteEditor);
    }
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
  frm.set_query("activity_type", "time_logs", function(doc) {
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
    if (typeof done === "function") { done(); }
    return;
  }
  frappe.db.get_list("Activity Type", {
    fields: ["name"],
    filters: { custom_project: project },
    order_by: "name asc",
    limit: 500
  }).then(function(rows) {
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
    if (typeof done === "function") { done(); }
  }).catch(function() {
    frm.allowed_activity_types = [];
    if (typeof done === "function") { done(); }
  });
}

function value_is_allowed(value, allowed) {
  var i = 0;
  while (i < (allowed || []).length) {
    if (allowed[i] === value) { return true; }
    i = i + 1;
  }
  return false;
}

function apply_rules_to_row(frm, cdt, cdn) {
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
  if (frm.doc.docstatus !== 0) { return; }
  if (!frm.doc.time_logs || frm.doc.time_logs.length === 0) { return; }
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
  onload: function(frm) {
    set_child_link_query(frm);
    if (frm.doc.parent_project) {
      fetch_allowed_activity_types(frm, function() {
        set_child_link_query(frm);
        update_all_rows(frm);
      });
    }
  },

  refresh: function(frm) {
    set_child_link_query(frm);
  },

  parent_project: function(frm) {
    if (frm.doc.parent_project) {
      fetch_allowed_activity_types(frm, function() {
        set_child_link_query(frm);
        update_all_rows(frm);
      });
    } else {
      frm.allowed_activity_types = [];
      set_child_link_query(frm);
      update_all_rows(frm); // clears disallowed values when project is removed
    }
  },

  custom_pb_rate: function(frm) {
    // Keep your convenience bulk-set behaviour (draft only)
    bulk_set_from_parent_rate(frm);
  }
});

frappe.ui.form.on("Timesheet Detail", {
  time_logs_add: function(frm, cdt, cdn) {
    // Ensure cache exists before applying rules
    var ensure = function() {
      apply_rules_to_row(frm, cdt, cdn);
      frm.refresh_field("time_logs");
    };
    if (frm.allowed_activity_types === undefined) {
      fetch_allowed_activity_types(frm, function() {
        set_child_link_query(frm);
        ensure();
      });
    } else {
      ensure();
    }
  }
});

// --- Total Spent Hrs ---
frappe.ui.form.on('Timesheet', {
    onload: function(frm) {
        if (frm.is_new()) {
            update_total_spent_hours(frm);
        }
    },
    employee: function(frm) {
        update_total_spent_hours(frm);
    },
    parent_project: function(frm) {
        update_total_spent_hours(frm);
    }
});

function update_total_spent_hours(frm) {
    if (frm.doc.employee && frm.doc.parent_project) {
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Timesheet",
                fields: ["total_hours"],
                filters: {
                    employee: frm.doc.employee,
                    parent_project: frm.doc.parent_project,
                    docstatus: 1
                },
                limit_page_length: 1000
            },
            callback: function(r) {
                if (r.message) {
                    const total = r.message.reduce((sum, row) => sum + row.total_hours, 0);
                    frm.set_value("custom_total_spent_hours", total);
                }
            }
        });
    }
}
