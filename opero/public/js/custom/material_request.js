// Opero: client scripts for Material Request
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// --- Project Fetch to Material Request Item ---
frappe.ui.form.on('Material Request', {  // Parent doctype
    custom_project: function(frm) {
        // When the custom_project field changes, update the project field in the child table
        frm.doc.items.forEach(function(row) {
            frappe.model.set_value(row.doctype, row.name, 'project', frm.doc.custom_project);
        });
        frm.refresh_field('items');  // Refresh the child table to reflect changes
    },
    refresh: function(frm) {
        // Optional: add any refresh logic if needed
        frm.fields_dict['items'].grid.get_field('project').get_query = function(doc, cdt, cdn) {
            return {
                filters: {
                    'parent': doc.name
                }
            };
        };
    }
});

frappe.ui.form.on('Material Request Item', {  // Child doctype
    // Handle the addition of new rows
    items_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        let parent_doc = frm.doc;
        
        if (parent_doc.custom_project) {
            frappe.model.set_value(cdt, cdn, 'project', parent_doc.custom_project);
            frm.refresh_field('items');
        }
    }
});

// --- Budget Line Filter ---
frappe.ui.form.on('Material Request', {
    custom_project: function(frm) {
        // When custom_project changes, update the custom_budget_line field in all child table rows
        frm.doc.items.forEach(function(row) {
            frappe.model.set_value(row.doctype, row.name, 'custom_budget_line', '');
        });

        // Refresh the child table to reflect the changes
        frm.refresh_field('items');
    },
    refresh: function(frm) {
        // Set a filter for custom_budget_line in the child table
        frm.fields_dict['items'].grid.get_field('custom_budget_line').get_query = function(doc, cdt, cdn) {
            return {
                filters: {
                    'project': frm.doc.custom_project // Ensure only budget lines related to the project are selectable
                }
            };
        };
    }
});
