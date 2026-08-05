// Opero: client scripts for Consultant Task
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// --- Hide Completion Field ---
frappe.ui.form.on('Consultant Task', {
    refresh: function(frm) {
        if (!frm.doc.project_manager) return;

        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                doctype: 'Employee',
                filters: { name: frm.doc.project_manager },
                fieldname: 'user_id'
            },
            callback: function(r) {
                if (r.message && r.message.user_id === frappe.session.user) {
                    frm.set_df_property('completion_status', 'hidden', 0); // Show
                } else {
                    frm.set_df_property('completion_status', 'hidden', 1); // Hide
                }
            }
        });
    }
});

// --- Auto Resize ---
frappe.ui.form.on('Consultant Task', {
    onload: function(frm) {
        function resizeEditor() {
            const editor_wrapper = frm.fields_dict['text_editor_pmrx']?.wrapper;
            if (!editor_wrapper) return;

            const editor = editor_wrapper.querySelector('[contenteditable="true"]');
            if (editor) {
                editor.style.overflowY = 'hidden';
                editor.style.height = 'auto'; // Reset
                editor.style.height = editor.scrollHeight + 'px';
            }
        }

        // Resize after field is loaded/rendered
        setTimeout(resizeEditor, 300);

        // Optional: Resize on content change (advanced editors may require MutationObserver)
        frm.fields_dict['text_editor_pmrx'].df.onchange = () => {
            setTimeout(resizeEditor, 100);
        };
    }
});
