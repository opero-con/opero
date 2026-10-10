"""Use Frappe's Blogger role for the publication publisher profile."""

import frappe
from frappe.permissions import add_permission, update_permission_property

from opero.patches.v0_4.rename_publication_publisher_profile import execute as rename_profile

LEGACY_ROLE = "Website Publication Publisher"
ROLE = "Blogger"
ROLE_PROFILE = "Blogger"
MODULE_PROFILE = "Website Publications"


def execute():
	if not frappe.db.exists("Role", ROLE):
		frappe.throw("The standard Blogger role is required for publication access.")

	# Transfer assignments, not arbitrary permissions attached to the obsolete role.
	_replace_role_rows("Has Role", {"parenttype": ["in", ["User", "Role Profile"]]})
	_replace_role_rows("Has Role", {"parenttype": "Workspace", "parent": "Site Content"})

	rename_profile()

	if not frappe.db.exists("Role Profile", ROLE_PROFILE):
		frappe.get_doc(
			{"doctype": "Role Profile", "role_profile": ROLE_PROFILE, "roles": [{"role": ROLE}]}
		).insert(ignore_permissions=True)
	else:
		profile = frappe.get_doc("Role Profile", ROLE_PROFILE)
		if ROLE not in {row.role for row in profile.roles}:
			profile.append("roles", {"role": ROLE})
			profile.save(ignore_permissions=True)

	if not frappe.db.exists("Module Profile", MODULE_PROFILE):
		frappe.get_doc(
			{
				"doctype": "Module Profile",
				"module_profile_name": MODULE_PROFILE,
				"block_modules": [
					{"module": module}
					for module in frappe.get_all("Module Def", pluck="name")
					if module not in {"Opero Site", "Opero"}
				],
			}
		).insert(ignore_permissions=True)
	else:
		profile = frappe.get_doc("Module Profile", MODULE_PROFILE)
		if any(row.module == "Opero" for row in profile.block_modules):
			profile.set("block_modules", [row for row in profile.block_modules if row.module != "Opero"])
			profile.save(ignore_permissions=True)

	for doctype in ("publication", "publication_type", "publication_topic"):
		frappe.reload_doc("opero_site", "doctype", doctype, force=True)
		name = frappe.unscrub(doctype)
		_replace_role_rows("Custom DocPerm", {"parent": name}, permission_rows=True)
		if frappe.db.exists("Custom DocPerm", {"parent": name}) and not frappe.db.exists(
			"Custom DocPerm", {"parent": name, "role": ROLE}
		):
			add_permission(name, ROLE)
			if doctype == "publication":
				for permission in ("create", "write"):
					update_permission_property(name, ROLE, 0, permission, 1)

	if not frappe.db.exists("Workspace", "Site Content"):
		frappe.reload_doc("opero_site", "workspace", "site_content", force=True)
	workspace = frappe.get_doc("Workspace", "Site Content")
	if ROLE not in {row.role for row in workspace.roles}:
		workspace.append("roles", {"role": ROLE}).db_insert()

	if frappe.db.exists("Role", LEGACY_ROLE):
		# Retire obsolete grants without transferring them to every Blogger user.
		for doctype in ("DocPerm", "Custom DocPerm"):
			frappe.db.delete(doctype, {"role": LEGACY_ROLE})
		frappe.delete_doc("Role", LEGACY_ROLE, ignore_permissions=True)
	frappe.clear_cache()


def _replace_role_rows(doctype, filters=None, permission_rows=False):
	for row in frappe.get_all(doctype, filters={"role": LEGACY_ROLE, **(filters or {})}, fields="*"):
		target = {"parent": row.parent, "role": ROLE}
		if permission_rows:
			target.update(permlevel=row.permlevel, if_owner=row.if_owner)
		else:
			target.update(parenttype=row.parenttype, parentfield=row.parentfield)
		if frappe.db.exists(doctype, target):
			# Keep the existing Blogger rule, including any deliberate permission restrictions.
			frappe.db.delete(doctype, {"name": row.name})
		else:
			frappe.db.set_value(doctype, row.name, "role", ROLE, update_modified=False)
