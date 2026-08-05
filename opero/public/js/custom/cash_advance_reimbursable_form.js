// Opero: client scripts for Cash Advance-Reimbursable Form
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// --- Calculations ---
frappe.ui.form.on('Expense Classification', {
    budget: function(frm, cdt, cdn) {
        update_row_claim(frm, cdt, cdn);
    },
    actual_spend: function(frm, cdt, cdn) {
        update_row_claim(frm, cdt, cdn);
    },
    classification_remove: function(frm) {
        update_totals(frm);
    }
});

// Function to calculate claim for a row and update totals
function update_row_claim(frm, cdt, cdn) {
    let row = locals[cdt][cdn]; // Access the row
    if (!row) return;

    // Calculate claim: budget - actual_spend
    let budget = parseFloat(row.budget) || 0;
    let actualSpend = parseFloat(row.actual_spend) || 0;
    let claim = budget - actualSpend;

    // Update claim in the child table
    frappe.model.set_value(cdt, cdn, 'claim', claim);

    // Call function to update totals in the parent doctype
    update_totals(frm);
}

// Function to update total fields in Cash Advance
function update_totals(frm) {
    let budget_total = 0;
    let spend_total = 0;
    let claim_total = 0;

    // Loop through all rows in the child table
    (frm.doc.classification || []).forEach(row => {
        let budget = parseFloat(row.budget) || 0;
        let actualSpend = parseFloat(row.actual_spend) || 0;
        let claim = parseFloat(row.claim) || 0;

        budget_total += budget;
        spend_total += actualSpend;
        claim_total += claim;
    });

    // Update parent doctype fields
    frm.set_value('budget_total', budget_total);
    frm.set_value('spend_total', spend_total);
    frm.set_value('claim_total', claim_total);
}

// --- Self Approval Warning by Call to Server Script ---
frappe.ui.form.on('Cash Advance-Reimbursable Form', {
    refresh: function(frm) {
        if (
            !frm.doc.__islocal &&
            !frm.doc.self_approval &&
            frm.doc.owner === frappe.session.user &&
            frm.doc.workflow_state === "Pending PM's Approval"
        ) {
            frappe.call({
                method: "Get Project Master Managers",
                callback: function(response) {
                    const users = (response.message || []).filter(
                        user => user.name !== frappe.session.user
                    );

                    const nameList = users
                        .map(user => `${user.first_name || ""} ${user.last_name || ""}`.trim())
                        .filter(name => name);

                    let names = "";
                    if (nameList.length === 1) {
                        names = nameList[0];
                    } else if (nameList.length === 2) {
                        names = `${nameList[0]} or ${nameList[1]}`;
                    } else if (nameList.length > 2) {
                        names = nameList.slice(0, -1).join(", ") + ", or " + nameList.slice(-1)[0];
                    }

                    if (names) {
                        frm.dashboard.set_headline(
                            `You should not approve your own request. Please escalate it to: ${names}.`
                        );
                    } else {
                        frm.dashboard.set_headline(
                            `You should not approve your own request. No other active Projects Master Manager found.`
                        );
                    }
                }
            });
        } else {
            frm.dashboard.set_headline('');
        }
    }
});

// --- Currency ---
frappe.ui.form.on('Cash Advance', {
    currency: function(frm) {
        update_currency_symbol_in_child_table(frm);
    },
    onload: function(frm) {
        update_currency_symbol_in_child_table(frm);
    }
});

function update_currency_symbol_in_child_table(frm) {
    if (frm.doc.currency) {
        (frm.doc.expense_classification || []).forEach(row => {
            frappe.model.set_value(row.doctype, row.name, 'currency', frm.doc.currency);
        });
        frm.refresh_field('expense_classification'); // Refresh the child table
    }
}

// Child table event to ensure the currency is always updated
frappe.ui.form.on('Expense Classification', {
    budget: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (frm.doc.currency) {
            frappe.model.set_value(cdt, cdn, 'currency', frm.doc.currency);
        }
    }
});

// --- Date & Personnel Autofill ---
frappe.ui.form.on('Cash Advance-Reimbursable Form', {
    onload: function(frm) {
        // Auto-set the Request Date if it's empty
        if (!frm.doc.request_date) {
            frm.set_value('request_date', frappe.datetime.get_today());
        }

        // Auto-set Personnel linked to the current user if it's empty
        if (!frm.doc.personnel) {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Employee',  // Using 'Employee' as per your database
                    filters: { user_id: frappe.session.user },
                    fieldname: 'name'
                },
                callback: function(response) {
                    if (response.message && response.message.name) {
                        frm.set_value('personnel', response.message.name);
                    }
                }
            });
        }
    }
});
