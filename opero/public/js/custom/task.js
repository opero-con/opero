// Opero: client scripts for Task
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// --- Days to Hours ---
frappe.ui.form.on('Task Time Allocation', {
    days: function(frm, cdt, cdn) {
        // Get the current row
        const row = locals[cdt][cdn];

        // Fetch the standard working hours from HR Settings
        frappe.db.get_single_value('HR Settings', 'standard_working_hours').then((standard_working_hours) => {
            // Calculate hours based on the days entered
            if (row.days && standard_working_hours) {
                const calculated_hours = row.days * standard_working_hours;
                // Update the hours field in the current row
                frappe.model.set_value(cdt, cdn, 'hours', calculated_hours);
            } else {
                // Reset hours if days are empty
                frappe.model.set_value(cdt, cdn, 'hours', 0);
            }

            // Refresh the child table row to show updated hours
            frm.refresh_field(cdt, cdn);

            // Call functions to update total hours and total days in parent document
            update_total_hours(frm);
            update_total_days(frm);
        });
    }
});

// Function to sum hours and update custom_total_hours in the parent document
function update_total_hours(frm) {
    let total_hours = 0;

    // Loop through each child row in the Task Time Allocation table
    frm.doc.custom_time_allocation.forEach(function(row) {
        total_hours += row.hours || 0;  // Sum the hours, defaulting to 0 if undefined
    });

    // Update the custom_total_hours field in the parent document
    frm.set_value('custom_total_hours', total_hours);
}

// Function to sum days and update custom_total_days in the parent document
function update_total_days(frm) {
    let total_days = 0;

    // Loop through each child row in the Task Time Allocation table
    frm.doc.custom_time_allocation.forEach(function(row) {
        total_days += row.days || 0;  // Sum the days, defaulting to 0 if undefined
    });

    // Update the custom_total_days field in the parent document
    frm.set_value('custom_total_days', total_days);
}

// --- Update task_end in TTD ---
frappe.ui.form.on('Task', {
    exp_end_date: function(frm) {
        // Ensure exp_end_date is not empty
        if (frm.doc.exp_end_date) {
            // Fetch all Task Time Distribution records linked to this Project Task
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Task Time Distribution',
                    filters: {
                        'project_task': frm.doc.name
                    },
                    fields: ['name', 'task_end']
                },
                callback: function(response) {
                    if (response.message && response.message.length > 0) {
                        let task_time_distributions = response.message;
                        
                        // Loop through each Task Time Distribution entry
                        task_time_distributions.forEach(function(task_time_distribution) {
                            // Only update if task_end is different from exp_end_date
                            if (task_time_distribution.task_end !== frm.doc.exp_end_date) {
                                frappe.call({
                                    method: 'frappe.client.set_value',
                                    args: {
                                        doctype: 'Task Time Distribution',
                                        name: task_time_distribution.name,
                                        fieldname: {
                                            'task_end': frm.doc.exp_end_date
                                        }
                                    },
                                    callback: function(updateResponse) {
                                        if (!updateResponse.exc) {
                                            console.log(`Task Time Distribution updated: ${task_time_distribution.name}`);
                                        } else {
                                            console.error(`Failed to update Task Time Distribution: ${task_time_distribution.name}`);
                                        }
                                    }
                                });
                            }
                        });
                    } else {
                        console.log('No Task Time Distribution records found.');
                    }
                },
                error: function(err) {
                    console.error('Error fetching Task Time Distribution records:', err);
                }
            });
        }
    }
});
