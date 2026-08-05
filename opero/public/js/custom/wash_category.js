// Opero: client scripts for WASH Category
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// --- Subcategory Options ---
frappe.ui.form.on('WASH Category', {
    category_name: function(frm) {
        let options_map = {
            "Business Management & Finance": [
                "Business Planning", 
                "Financial Management", 
                "Accounting"
            ],
            "Operations & Supply Chain": [
                "Operational Efficiency, SOPs", 
                "Supply Chain Development"
            ],
            "Human Resources & Organizational Development": [
                "HRM", 
                "Organizational Capacity Building/Restructuring", 
                "Workforce Development"
            ],
            "Leadership & Governance": [
                "Leadership", 
                "Governance"
            ],
            "Social Impact & Sustainability": [
                "Gender + Social Equity", 
                "Social-BOP Impact", 
                "Sustainability", 
                "Circular Economy"
            ],
            "Marketing & Sales": [
                "CRM/Customer Engagement/Communication/Branding", 
                "Market Research and Analysis", 
                "Marketing and Sales"
            ],
            "Legal & Regulatory": [
                "Legal Services/Licensing/Certification", 
                "Policy/Advocacy"
            ],
            "WASH (Water, Sanitation, and Hygiene) Technical Skills": [
                "General WASH Technology Assessment & Selection", 
                "Climate Resilience (WASH related)", 
                "Water", 
                "Sanitation", 
                "Female Health and Hygiene"
            ],
            "Digitalization & Data Management": [
                "Digital Tools/Data Analytics", 
                "Impact Management & Monitoring (IMM)", 
                "Monitoring, Evaluation & Learning (MEL)", 
                "ESG Compliance"
            ],
            "Finance & Investment Readiness": [
                "Investment Readiness Advisory Services", 
                "Transaction Advisory and Due Diligence", 
                "Innovative Finance - Blended Finance Models", 
                "Public-Private Partnerships", 
                "Technical Writing and Proposal Development (related to finance)"
            ]
        };

        let selected_category = frm.doc.category_name;
        let subcategories = options_map[selected_category] || [];

        frm.set_df_property("subcategory_name", "options", subcategories.join("\n"));
        frm.refresh_field("subcategory_name");
    }
});
