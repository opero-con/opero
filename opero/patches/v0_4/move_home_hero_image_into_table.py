import frappe
from frappe.utils import cstr


def execute():
	if not frappe.db.exists("DocType", "Home Page"):
		return

	frappe.reload_doc("opero_site", "doctype", "hero_image")
	if not frappe.db.table_exists("Hero Image"):
		return

	# Read legacy Singles keys directly. get_single_value() throws once Home Page
	# meta no longer lists hero_image (already-migrated Cubenet, or pre_model_sync
	# after a partial update), which aborted every auto-migrate.
	image = _legacy_single("hero_image")
	if not image:
		return

	existing = frappe.get_all(
		"Hero Image",
		filters={"parent": "Home Page", "parenttype": "Home Page", "parentfield": "hero_images"},
		fields=["name", "image", "idx"],
		order_by="idx",
	)
	if existing:
		# Table model already in use (typical Cubenet). Drop any leftover Singles keys.
		_clear_legacy_singles()
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
			"image_alt": _legacy_single("hero_image_alt"),
			"note": _legacy_single("hero_note") or "Kenya · East Africa",
		}
	).insert(ignore_permissions=True)
	_clear_legacy_singles()


def _legacy_single(field: str) -> str:
	value = frappe.db.sql(
		"""
		SELECT value
		FROM tabSingles
		WHERE doctype = %s AND field = %s
		""",
		("Home Page", field),
	)
	return cstr(value[0][0] if value else "").strip()


def _clear_legacy_singles() -> None:
	frappe.db.sql(
		"""
		DELETE FROM tabSingles
		WHERE doctype = %s AND field IN (%s, %s, %s)
		""",
		("Home Page", "hero_image", "hero_image_alt", "hero_note"),
	)
