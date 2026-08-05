// Opero: client scripts for Travel Request
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// --- Mileage Section Visibility ---
frappe.ui.form.on('Travel Request', { // Trigger when the form is loaded or refreshed
    refresh: function(frm) {
        updateSectionVisibility(frm);
    },
    // Trigger on validate to ensure visibility is correct before saving
    validate: function(frm) {
        updateSectionVisibility(frm);
    },
    // Trigger when a row is added to the Travel Itinerary child table
    'itinerary_add': function(frm, cdt, cdn) {
        updateSectionVisibility(frm);
    },
    // Trigger when a row is removed from the Travel Itinerary child table
    'itinerary_remove': function(frm, cdt, cdn) {
        updateSectionVisibility(frm);
    },
    // Trigger when the custom_travel_mode field in any row of the child table is updated
    'itinerary': {
        custom_travel_mode: function(frm, cdt, cdn) {
            updateSectionVisibility(frm);
        }
    }
});

// Function to update the visibility of the custom_mileage_section field
function updateSectionVisibility(frm) {
    // Determine if the 'Rented Car' option is selected in any row
    let shouldShowMileageSection = false;

    if (Array.isArray(frm.doc.itinerary)) {
        shouldShowMileageSection = frm.doc.itinerary.some(row => row.custom_travel_mode === "Rented Car");
    }

    // Get the current hidden state of the custom_mileage_claim field
    const isCurrentlyHidden = frm.fields_dict['custom_mileage_section'].df.hidden;

    // Update field visibility if the state has changed
    if (shouldShowMileageSection && isCurrentlyHidden) {
        // Show the field if it should be shown but is currently hidden
        frm.set_df_property('custom_mileage_section', 'hidden', false);
        frm.refresh_field('custom_mileage_section');
    } else if (!shouldShowMileageSection && !isCurrentlyHidden) {
        // Hide the field if it should be hidden but is currently shown
        frm.set_df_property('custom_mileage_section', 'hidden', true);
        frm.refresh_field('custom_mileage_section');
    }
}

// --- Nights in Travel Request ---
frappe.ui.form.on('Accomodation', {
    check_in_date: function(frm, cdt, cdn) {
        calculate_number_of_days(frm, cdt, cdn);
    },
    check_out_date: function(frm, cdt, cdn) {
        calculate_number_of_days(frm, cdt, cdn);
    }
});

function calculate_number_of_days(frm, cdt, cdn) {
    // Get the current row in the child table
    let row = locals[cdt][cdn];

    if (row.check_in_date && row.check_out_date) {
        const checkInDate = new Date(row.check_in_date);
        const checkOutDate = new Date(row.check_out_date);

        // Ensure that check-out date is not earlier than check-in date
        if (checkOutDate >= checkInDate) {
            const timeDifference = checkOutDate - checkInDate;
            const numberOfDays = Math.ceil(timeDifference / (1000 * 3600 * 24)); // Convert milliseconds to days

            frappe.model.set_value(cdt, cdn, 'nights', numberOfDays);
        } else {
            frappe.msgprint(__('Check-out date cannot be earlier than check-in date.'));
            frappe.model.set_value(cdt, cdn, 'nights', 0);
        }
    } else {
        frappe.model.set_value(cdt, cdn, 'nights', 0);
    }
}

// --- personnel default and banner ---
frappe.ui.form.on('Travel Request', {
    refresh: function(frm) {
        show_banner(frm);
    },
    
    workflow_state: function(frm) {
        show_banner(frm);
    },

    onload: function(frm) {
        // Only set the employee field if the document is new
        if (frm.is_new()) {
            // Get the logged-in user
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    'doctype': 'Employee',
                    'filters': {'user_id': frappe.session.user},
                    'fieldname': 'name'
                },
                callback: function(r) {
                    if (r.message) {
                        // Set the employee field to the employee linked to the logged-in user
                        frm.set_value('employee', r.message.name);
                    }
                }
            });
        }
    }
});

function show_banner(frm) {
    // Clear any previous alerts to avoid duplication
    frm.dashboard.clear_headline();

    // Ensure the document is saved and the workflow state is 'Draft'
    if (!frm.is_new() && frm.doc.workflow_state === 'Draft') {
        // Fetch the custom_project_manager field from the document
        const project_manager = frm.doc.custom_pm_name || 'the project manager';

        // Set the headline alert with the dynamic project manager
        frm.dashboard.set_headline_alert(`Submit this for review by the PM (${project_manager}).
The Submit button is under "Actions."`, 'blue');
    }
}

// --- Per Diem & Mileage Claim Calculations ---
frappe.ui.form.on('Travel Request', {
    custom_number_of_days: function(frm) {
        frm.trigger('calculate_custom_total_per_diem');
    },
    custom_per_diem_amount: function(frm) {
        frm.trigger('calculate_custom_total_per_diem');
    },
    calculate_custom_total_per_diem: function(frm) {
        if (frm.doc.custom_number_of_days && frm.doc.custom_per_diem_amount) {
            frm.set_value('custom_total_per_diem', frm.doc.custom_number_of_days * frm.doc.custom_per_diem_amount);
        } else {
            frm.set_value('custom_total_per_diem', 0);
        }
    },
    custom_mileage_claim: function(frm) {
        frm.trigger('calculate_custom_mileage_amount');
    },
    custom_mileage_rate: function(frm) {
        frm.trigger('calculate_custom_mileage_amount');
    },
    calculate_custom_mileage_amount: function(frm) {
        if (frm.doc.custom_mileage_claim && frm.doc.custom_mileage_rate) {
            frm.set_value('custom_mileage_amount', frm.doc.custom_mileage_claim * frm.doc.custom_mileage_rate);
        } else {
            frm.set_value('custom_mileage_amount', 0);
        }
    }
});
