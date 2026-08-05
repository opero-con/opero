// Opero: client scripts for Project Time Allocation
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// --- Hours ---
frappe.ui.form.on('Project Time Allocation', {
    refresh: function(frm) {
        calculate_total_hours(frm);
    },
    // Listen to changes in the time_allocation_detail child table
    time_allocation_detail_add: function(frm) {
        calculate_total_hours(frm);
    },
    time_allocation_detail_remove: function(frm) {
        calculate_total_hours(frm);
    },
    validate: function(frm) {
        calculate_total_hours(frm);
    }
});

function calculate_total_hours(frm) {
    let total_days = 0;

    // Loop through all the rows in the time_allocation_detail child table
    frm.doc.time_allocation_detail.forEach(row => {
        if (row.days) {
            total_days += row.days;
        }
    });

    // Fetch the standard working hours from HR Settings
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'HR Settings',
            fieldname: 'standard_working_hours'
        },
        callback: function(r) {
            if (r.message && r.message.standard_working_hours) {
                let standard_working_hours = r.message.standard_working_hours;

                // Multiply total days by standard working hours
                let total_hours = total_days * standard_working_hours;

                // Set the result to the hours field in the parent doctype
                frm.set_value('hours', total_hours);
            } else {
                frappe.msgprint(__('Unable to fetch standard working hours from HR Settings.'));
            }
        }
    });
}

// --- Completed On Compulsory ---
frappe.ui.form.on('Project Time Allocation', {
    validate: function(frm) {
        // Check if the status is 'Completed' and the 'completed_on' field is empty
        if (frm.doc.status === 'Completed' && !frm.doc.completed_on) {
            frappe.msgprint(__('Please fill in the Completed On field before submitting.'));
            frappe.validated = false; // Prevents form submission
        }
    },
    refresh: function(frm) {
        // Set the field to be required dynamically based on the status
        frm.toggle_reqd('completed_on', frm.doc.status === 'Completed');
    }
});

// --- Days ---
frappe.ui.form.on('Time Allocation Detail', {
    date_from: function(frm, cdt, cdn) {
        calculate_days_between_dates(frm, cdt, cdn);
    },
    date_to: function(frm, cdt, cdn) {
        calculate_days_between_dates(frm, cdt, cdn);
    }
});

function calculate_days_between_dates(frm, cdt, cdn) {
    // Get the current row in the child table
    let row = locals[cdt][cdn];

    if (row.date_from && row.date_to) {
        const dateFrom = new Date(row.date_from);
        const dateTo = new Date(row.date_to);

        // Ensure that date_to is not earlier than date_from
        if (dateTo >= dateFrom) {
            const timeDifference = dateTo - dateFrom;
            const numberOfDays = Math.ceil(timeDifference / (1000 * 3600 * 24)); // Convert milliseconds to days

            frappe.model.set_value(cdt, cdn, 'days', numberOfDays);
        } else {
            frappe.msgprint(__('End date cannot be earlier than start date.'));
            frappe.model.set_value(cdt, cdn, 'days', 0);
        }
    } else {
        frappe.model.set_value(cdt, cdn, 'days', 0);
    }
}

// --- Project Task ---
frappe.ui.form.on('Project Time Allocation', {
    onload: function(frm) {
        set_project_task_filter(frm);
    },
    refresh: function(frm) {
        set_project_task_filter(frm);
    }
});

function set_project_task_filter(frm) {
    frm.fields_dict['time_allocation_detail'].grid.get_field('project_task').get_query = function(doc, cdt, cdn) {
        let row = locals[cdt][cdn];

        // If no project is selected, return an empty filter to prevent any tasks from showing
        if (!frm.doc.project) {
            return {
                filters: {
                    'name': ''  // Return no results by using an empty name filter
                }
            };
        } 
        // If project is set, filter tasks by project
        else {
            return {
                filters: {
                    'project': frm.doc.project  // Show tasks linked to the selected project
                }
            };
        }
    };
}
