// Opero: client scripts for Project Budget
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// --- Chart in Project Budget ---
frappe.ui.form.on('Project Budget', {
    refresh: function (frm) {
        if (!frm.doc.project || !frm.doc.budget_items) return;

        frm.fields_dict.timesheet_budget_chart.$wrapper.empty();

        frappe.call({
            method: "project-budget-timesheet-actuals",
            type: "GET",
            args: { project: frm.doc.project },
            callback: function (r) {
                const actuals = r.message || {};
                const budgeted = {};

                frm.doc.budget_items.forEach(row => {
                    if (row.account && row.amount) {
                        budgeted[row.account] = row.amount;
                    }
                });

                const labels = Object.keys(budgeted);
                const budget_values = labels.map(acc => budgeted[acc] || 0);
                const actual_values = labels.map(acc => actuals[acc] || 0);

                const chart_data = {
                    labels: labels,
                    datasets: [
                        { name: "Budgeted", values: budget_values },
                        { name: "Actual", values: actual_values }
                    ]
                };

                new frappe.Chart(frm.fields_dict.timesheet_budget_chart.$wrapper[0], {
                    title: "Budget vs Actual Spend",
                    data: chart_data,
                    type: 'bar',
                    colors: ['#5e64ff', '#ffa00a'],
                    height: 250
                });
            }
        });
    }
});
