"""Add the Product publication type and file the technology pages under it."""

import frappe

from opero.opero_site.utils import PRODUCT_PUBLICATION_TYPE

PRODUCT_DESCRIPTION = "A product page, such as PuPu Pump, Gulper, or PitVaq. The card opens that page."
OVERVIEW_DESCRIPTION = "A shareable overview, such as the Opero Project Portfolio PDF."
PRODUCT_SLUGS = ("gulper", "pitvaq", "pupu-pump")


def execute():
	if not frappe.db.table_exists("Publication Type"):
		return
	_ensure_product_type()
	if frappe.db.exists("Publication Type", "Overview"):
		frappe.db.set_value(
			"Publication Type", "Overview", "description", OVERVIEW_DESCRIPTION, update_modified=False
		)
	if not frappe.db.table_exists("Publication"):
		return
	for slug in PRODUCT_SLUGS:
		name = frappe.db.get_value("Publication", {"slug": slug})
		if not name:
			continue
		doc = frappe.get_doc("Publication", name)
		if doc.publication_type == PRODUCT_PUBLICATION_TYPE:
			continue
		doc.publication_type = PRODUCT_PUBLICATION_TYPE
		doc.save(ignore_permissions=True)


def _ensure_product_type() -> None:
	if frappe.db.exists("Publication Type", PRODUCT_PUBLICATION_TYPE):
		frappe.db.set_value(
			"Publication Type",
			PRODUCT_PUBLICATION_TYPE,
			"description",
			PRODUCT_DESCRIPTION,
			update_modified=False,
		)
		return
	frappe.get_doc(
		{
			"doctype": "Publication Type",
			"title": PRODUCT_PUBLICATION_TYPE,
			"description": PRODUCT_DESCRIPTION,
		}
	).insert(ignore_permissions=True)
