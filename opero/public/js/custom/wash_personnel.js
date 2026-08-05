// Opero: client scripts for WASH Personnel
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// --- New Contact Button ---
frappe.ui.form.on('WASH Personnel', {
    refresh: function(frm) {
        if (frm.doc.contact) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Contact',
                    name: frm.doc.contact
                },
                callback: function(r) {
                    if (r.message) {
                        let contact = r.message;

                        // Extract phone numbers
                        let phone_numbers = contact.phone_nos ? contact.phone_nos.map(ph => ph.phone).join(', ') : 'N/A';

                        let contact_html = `
                            <div style="margin-bottom: 10px;">
                                <b>${contact.full_name || 'Unnamed Contact'}</b><br>
                                ${contact.email_id ? '📧 ' + contact.email_id + '<br>' : ''}
                                ${phone_numbers ? '📞 ' + phone_numbers + '<br>' : ''}
                            </div>
                        `;

                        frm.set_df_property('contact_html', 'options', contact_html);
                        frm.refresh_field('contact_html');
                    } else {
                        set_add_contact_button(frm);
                    }
                }
            });
        } else {
            set_add_contact_button(frm);
        }
    }
});

// Function to set the 'Add Contact' button
function set_add_contact_button(frm) {
    let add_contact_html = `
        <div>
            Select contact from above or 
            <button class="btn btn-xs btn-primary" id="add_contact_btn">
                Add Contact
            </button>
        </div>
    `;

    frm.set_df_property('contact_html', 'options', add_contact_html);
    frm.refresh_field('contact_html');

    // Add event listener to the button
    setTimeout(() => {
        $('#add_contact_btn').click(() => {
            frappe.new_doc('Contact', {
                links: [{
                    link_doctype: 'WASH Personnel',
                    link_name: frm.doc.name
                }]
            });
        });
    }, 100);
}

// --- Filter ---
frappe.ui.form.on('WASH Personnel', {
    refresh: function(frm) {
        frm.fields_dict["wash_expert_profile"].grid.get_field("subcategory_name").get_query = function(doc, cdt, cdn) {
            let row = locals[cdt][cdn]; // Get the current row in the child table

            if (!row.category_name) {
                return { filters: {} }; // Return empty filters if no category is selected
            }

            return {
                filters: {
                    parent_wash_category: row.category_name  // Filter based on selected category
                }
            };
        };
    }
});
