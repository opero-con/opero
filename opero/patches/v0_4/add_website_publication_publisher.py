"""Create a publication-only role and reusable Desk access profiles."""

import frappe
from frappe.permissions import add_permission, update_permission_property

ROLE = "Website Publication Publisher"
MODULE_PROFILE = "Website Publications"


def execute():
	if not frappe.db.exists("Role", ROLE):
		frappe.get_doc({"doctype": "Role", "role_name": ROLE, "desk_access": 1}).insert(
			ignore_permissions=True
		)
	if not frappe.db.exists("Role Profile", ROLE):
		frappe.get_doc({"doctype": "Role Profile", "role_profile": ROLE, "roles": [{"role": ROLE}]}).insert(
			ignore_permissions=True
		)
	if not frappe.db.exists("Module Profile", MODULE_PROFILE):
		modules = frappe.get_all("Module Def", pluck="name")
		frappe.get_doc(
			{
				"doctype": "Module Profile",
				"module_profile_name": MODULE_PROFILE,
				"block_modules": [
					{"module": module} for module in modules if module not in {"Opero Site", "Opero"}
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
		if frappe.db.exists("Custom DocPerm", {"parent": name}):
			add_permission(name, ROLE)
			if doctype == "publication":
				for permission in ("create", "write"):
					update_permission_property(name, ROLE, 0, permission, 1)
	if not frappe.db.exists("Workspace", "Site Content"):
		frappe.reload_doc("opero_site", "workspace", "site_content", force=True)
	workspace = frappe.get_doc("Workspace", "Site Content")
	if ROLE not in {row.role for row in workspace.roles}:
		workspace.append("roles", {"role": ROLE}).db_insert()
	frappe.clear_cache(doctype="Workspace")
