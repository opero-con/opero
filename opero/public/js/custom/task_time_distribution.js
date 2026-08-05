// Opero: client scripts for Task Time Distribution
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// --- Re-Distribute Month(s) ---
frappe.ui.form.on('Task Time Distribution', {
    refresh: function (frm) {
        frm.add_custom_button(
            frm.doc.task_time_distribution_spread.length > 0 ? 'Re-Distribute Month(s)' : 'Distribute Month(s)',
            async function () {
                if (!frm.doc.project_task) {
                    frappe.msgprint(__('Please select a project task before proceeding.'));
                    frm.set_df_property('section_break_ttd', 'hidden', 1);
                    return;
                }

                try {
                    // Fetch the Task document
                    let task = await frappe.db.get_doc('Task', frm.doc.project_task);
                    
                    if (task.exp_start_date && task.exp_end_date) {
                        // Calculate the months between start and end dates
                        const months = getMonthsBetweenDates(task.exp_start_date, task.exp_end_date);

                        // Populate the child table with these months
                        updateTaskTimeDistributionSpread(months, frm);
                        
                        // Save the previous project task to track changes
                        frm.doc._previous_task = frm.doc.project_task;
                        
                        // Show the section
                        frm.set_df_property('section_break_ttd', 'hidden', 0);
                    }
                } catch (error) {
                    console.error("Error fetching task details:", error);
                    frappe.msgprint(__('Error fetching task details.'));
                }
            }
        );
    },

    onload: function (frm) {
        // Hide section if no project task is selected
        frm.set_df_property('section_break_ttd', 'hidden', frm.doc.project_task ? 0 : 1);
    }
});

// Custom function to ensure consistent month abbreviation format
function formatMonth(year, monthIndex) {
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return `${monthNames[monthIndex]} ${year}`;
}

// Function to get unique months between two dates
function getMonthsBetweenDates(start_date, end_date) {
    const start = new Date(start_date);
    const end = new Date(end_date);
    const months = [];

    // Ensure that the end date is not incorrectly extended
    const lastDayOfMonth = new Date(end.getFullYear(), end.getMonth() + 1, 0).getDate();
    if (end.getDate() !== 1 && end.getDate() !== lastDayOfMonth) {
        end.setMonth(end.getMonth() + 1);
        end.setDate(0); // Move to the last day of that month
    }

    while (start <= end) {
        months.push(formatMonth(start.getFullYear(), start.getMonth()));
        start.setMonth(start.getMonth() + 1);
    }

    return [...new Set(months)]; // Ensure uniqueness
}

// Function to update child table with unique months
function updateTaskTimeDistributionSpread(months, frm) {
    const existingMonths = frm.doc.task_time_distribution_spread.map(row => row.month);

    months.forEach(month => {
        if (!existingMonths.includes(month)) {
            let row = frm.add_child('task_time_distribution_spread');
            row.month = month;
            row.time_spread = 0; // Default value
        }
    });

    frm.refresh_field('task_time_distribution_spread');
}

// --- TTDS Days to Hrs ---
frappe.ui.form.on('Task Time Distribution Spread', {
    days_spread: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];

        // Fetch the standard working hours from HR Settings
        frappe.db.get_single_value('HR Settings', 'standard_working_hours').then((standard_working_hours) => {
            // Multiply days_spread by standard_working_hours and set it to time_spread
            row.time_spread = row.days_spread * standard_working_hours;

            // Refresh only the changed row
            frm.refresh_field('task_time_distribution_spread', cdn);
        });
    }
});

// --- field population and total distribution ---
frappe.ui.form.on('Task Time Distribution', {
    onload: function(frm) {
        // Update totals with rounded values
        update_total_days_distributed(frm);

        // Update task and project dates
        update_task_and_project_dates(frm);
    },

    project_task: function(frm) {
        update_task_and_project_dates(frm);
    },

    validate: function(frm) {
        const spread = flt(frm.doc.total_days_distributed);
        const allocated = flt(frm.doc.days_allocated);

        // Ensure precision to 2 decimal places
        const roundedSpread = Math.round(spread * 100) / 100;  // rounding to 2 decimal places
        const roundedAllocated = Math.round(allocated * 100) / 100;  // rounding to 2 decimal places
    
        if (roundedSpread !== roundedAllocated && !(roundedSpread === 0 && roundedAllocated > 0)) {
            let direction = roundedSpread > roundedAllocated ? "more" : "less";
            frappe.throw(__(`Total days distributed (${roundedSpread}) is ${direction} than allocated days (${roundedAllocated}) in the Project Task.`));
        }
    },
    
    after_save: function(frm) {
        const spread = flt(frm.doc.total_days_distributed);
        const allocated = flt(frm.doc.days_allocated);

        // Ensure precision to 2 decimal places
        const roundedSpread = Math.round(spread * 100) / 100;  // rounding to 2 decimal places
        const roundedAllocated = Math.round(allocated * 100) / 100;  // rounding to 2 decimal places
    
        if (roundedSpread === 0 && roundedAllocated > 0) {
            frappe.msgprint(__('Please populate the Distribution Detail table.'));
        }
    }
});

frappe.ui.form.on('Task Time Distribution Spread', {
    days_spread: function(frm, cdt, cdn) {
        update_total_days_distributed(frm);
    },
    task_time_distribution_spread_remove: function(frm) {
        update_total_days_distributed(frm);
    }
});

function update_total_days_distributed(frm) {
    let total = 0;
    (frm.doc.task_time_distribution_spread || []).forEach(row => {
        total += flt(row.days_spread);
    });

    // Round the total days distributed to 2 decimal places
    total = Math.round(total * 100) / 100;  // rounding to 2 decimal places

    frm.set_value("total_days_distributed", total);
}

function update_task_and_project_dates(frm) {
    if (frm.doc.project_task) {
        frappe.db.get_value('Task', frm.doc.project_task, ['exp_start_date', 'exp_end_date', 'project'])
            .then(r => {
                if (r.message) {
                    let updated = false;

                    if (r.message.project && frm.doc.project !== r.message.project) {
                        frm.set_value('project', r.message.project);
                        updated = true;
                    }

                    if (r.message.exp_start_date && frm.doc.task_start !== r.message.exp_start_date) {
                        frm.set_value('task_start', r.message.exp_start_date);
                        updated = true;
                    }

                    if (r.message.exp_end_date && frm.doc.task_end !== r.message.exp_end_date) {
                        frm.set_value('task_end', r.message.exp_end_date);
                        updated = true;
                    }

                    if (r.message.project) {
                        frappe.db.get_value('Project', r.message.project, ['expected_start_date', 'expected_end_date'])
                            .then(pr => {
                                if (pr.message) {
                                    let proj_updated = false;

                                    if (frm.doc.project_start_date !== pr.message.expected_start_date) {
                                        frm.set_value('project_start_date', pr.message.expected_start_date || null);
                                        proj_updated = true;
                                    }

                                    if (frm.doc.project_end_date !== pr.message.expected_end_date) {
                                        frm.set_value('project_end_date', pr.message.expected_end_date || null);
                                        proj_updated = true;
                                    }

                                    // Only save if something was actually updated AND the doc isn't new
                                    if ((updated || proj_updated) && !frm.doc.__islocal) {
                                        frm.save();
                                    }
                                }
                            });
                    }
                }
            });
    }
}
