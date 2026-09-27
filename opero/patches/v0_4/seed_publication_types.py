"""Turn the fixed Publication type options into editable Publication Type records."""

import frappe

DEFAULT_TYPES = {
	"Case study": "A long write-up of a technology or programme, as an article, a PDF, or both.",
	"Digest": "An issue of the PuPu Pump Digest.",
	"Newsletter": "A company update.",
	"Overview": "A product page (PuPu Pump, Gulper, PitVaq) or the Opero Project Portfolio PDF.",
	"Project": "A short record of delivered work that is not already a case study.",
}


def execute():
	used = frappe.db.sql_list(
		"""
		SELECT DISTINCT TRIM(publication_type)
		FROM `tabPublication`
		WHERE IFNULL(TRIM(publication_type), '') != ''
		"""
	)
	for title in [*DEFAULT_TYPES, *used]:
		if frappe.db.exists("Publication Type", title):
			continue
		frappe.get_doc(
			{"doctype": "Publication Type", "title": title, "description": DEFAULT_TYPES.get(title)}
		).insert(ignore_permissions=True)
