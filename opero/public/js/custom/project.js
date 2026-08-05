// Opero: client scripts for Project
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// --- Time_allocation_handler ---
frappe.ui.form.on('Project', {
    refresh: function(frm) {
        calculate_total_hours(frm); // Recalculate on refresh
    },
    custom_time_allocation_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        row.project = frm.doc.name; // Set the project field to the current project's name
        frm.refresh_field('custom_time_allocation'); // Refresh the child table
        calculate_total_hours(frm); // Recalculate total hours after adding a row
    },
    custom_time_allocation_remove: function(frm, cdt, cdn) {
        calculate_total_hours(frm); // Recalculate total hours after removing a row
    },
    'custom_time_allocation.hours': function(frm, cdt, cdn) {
        calculate_total_hours(frm); // Recalculate total hours when hours field changes
    }
});

function calculate_total_hours(frm) {
    var total_hours = 0;
    $.each(frm.doc.custom_time_allocation || [], function(i, row) {
        total_hours += row.hours ? parseFloat(row.hours) : 0; // Ensure hours is numeric and defined
    });
    frm.set_value('custom_total_project_allocated_hours', total_hours); // Update total allocated hours
}

// --- Costing & Margin Hide ---
frappe.ui.form.on('Project', {
    refresh: function(frm) {
        const allowedUsers = ['nicola@opero-services.com', 'ingrid@opero-services.com', 'patrick@reyal.biz'];
        const currentUser = frappe.session.user;

        // Check if the current user is in the allowed list
        if (!allowedUsers.includes(currentUser)) {
            // Hide the sections completely
            frm.toggle_display('project_details', false);
            frm.toggle_display('margin', false);
        }
    }
});
