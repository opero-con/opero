// Opero: client scripts for Actual Spend
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// --- Child Table ---
frappe.ui.form.on('Actual Spend', {
    cash_advance: function(frm) {
        if (frm.doc.cash_advance) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Cash Advance-Reimbursable Form',
                    name: frm.doc.cash_advance
                },
                callback: function(r) {
                    if (r.message) {
                        frm.clear_table('classifications');
                        (r.message.classifications || []).forEach(row => {
                            frm.add_child('classifications', {
                                classification: row.classification,
                                budget: row.budget
                            });
                        });
                        frm.refresh_field('classifications');
                    }
                }
            });
        }
    }
});
