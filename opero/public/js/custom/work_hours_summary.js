// Opero: client scripts for Work Hours Summary
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// --- Autopopulate Months ---
frappe.ui.form.on('Work Hours Summary', {
    onload: function(frm) {
        // Check if the document is new
        if (frm.is_new()) {
            // List of months
            const months = [
                'January', 'February', 'March', 'April', 'May', 
                'June', 'July', 'August', 'September', 'October', 
                'November', 'December'
            ];

            // Initialize the months in the child table
            if (frm.doc.distribution_detail && frm.doc.distribution_detail.length === 0) {
                months.forEach(month => {
                    let row = frm.add_child('distribution_detail');
                    row.month = month;
                    row.days = 0; // Initialize days to 0
                });
                frm.refresh_field('distribution_detail');
            }
        }
    },

    year: function(frm) {
        if (frm.doc.year) {
            // Loop through the child table and update the days based on the year
            frm.doc.distribution_detail.forEach(row => {
                let month_index = get_month_index(row.month); // Get the month's index
                let days_in_month = get_days_in_month(month_index, frm.doc.year); // Calculate the days
                row.days = days_in_month; // Set the days field
            });
            frm.refresh_field('distribution_detail'); // Refresh the child table to reflect the changes
        }
    }
});

// Function to get the index of the month (0-based for JavaScript's Date object)
function get_month_index(month) {
    const months = {
        'January': 0,
        'February': 1,
        'March': 2,
        'April': 3,
        'May': 4,
        'June': 5,
        'July': 6,
        'August': 7,
        'September': 8,
        'October': 9,
        'November': 10,
        'December': 11
    };
    return months[month];
}

// Function to calculate the number of days in a month for a given year
function get_days_in_month(month_index, year) {
    return new Date(year, month_index + 1, 0).getDate(); // JavaScript months are 0-indexed
}
