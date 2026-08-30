import frappe
from frappe.utils import cstr


def execute():
	if not frappe.db.exists("DocType", "Home Page"):
		return

	frappe.reload_doc("opero_site", "doctype", "hero_image")
	if not frappe.db.table_exists("Hero Image"):
		return

	image = _single("hero_image")
	if not image:
		return

	existing = frappe.get_all(
		"Hero Image",
		filters={"parent": "Home Page", "parenttype": "Home Page", "parentfield": "hero_images"},
		fields=["name", "image", "idx"],
		order_by="idx",
	)
	if existing and cstr(existing[0].image).strip() == image:
		return

	frappe.db.sql(
		"""
		UPDATE `tabHero Image`
		SET idx = idx + 1
		WHERE parent = %s AND parenttype = %s AND parentfield = %s
		""",
		("Home Page", "Home Page", "hero_images"),
	)
	frappe.get_doc(
		{
			"doctype": "Hero Image",
			"parent": "Home Page",
			"parenttype": "Home Page",
			"parentfield": "hero_images",
			"idx": 1,
			"image": image,
			"image_alt": _single("hero_image_alt"),
			"note": _single("hero_note") or "Kenya · East Africa",
		}
	).insert(ignore_permissions=True)


def _single(field: str) -> str:
	return cstr(frappe.db.get_single_value("Home Page", field)).strip()
