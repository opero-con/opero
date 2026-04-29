"""Move Zoho Books mappings from child tables and custom fields into Integration Mapping."""

import frappe

INTEGRATION = "zoho_books"


def execute():
	if not frappe.db.table_exists("tabIntegration Mapping"):
		frappe.logger().warning("Integration Mapping table not found — skipping migration")
		return

	_migrate_personnel()
	_migrate_projects()
	_migrate_tasks()
	_migrate_timesheet_entries()
	frappe.db.commit()


def _upsert(entity_type, local_name, remote_id, remote_name=""):
	if not local_name or not remote_id:
		return
	existing = frappe.db.get_value(
		"Integration Mapping",
		{"integration": INTEGRATION, "entity_type": entity_type, "local_name": local_name},
		"name",
	)
	if existing:
		frappe.db.set_value("Integration Mapping", existing, {"remote_id": remote_id, "remote_name": remote_name})
	else:
		frappe.get_doc({
			"doctype": "Integration Mapping",
			"integration": INTEGRATION,
			"entity_type": entity_type,
			"local_name": local_name,
			"remote_id": remote_id,
			"remote_name": remote_name,
		}).insert(ignore_permissions=True)


def _migrate_personnel():
	if not frappe.db.table_exists("tabZoho Books Personnel Mapping"):
		return
	rows = frappe.db.sql(
		"SELECT personnel_id, zoho_user_id, zoho_user_name FROM `tabZoho Books Personnel Mapping`",
		as_dict=True,
	)
	for row in rows:
		_upsert("Employee", row.personnel_id, row.zoho_user_id, row.zoho_user_name or "")
	frappe.logger().info(f"Migrated {len(rows)} personnel mapping(s)")


def _migrate_projects():
	if not frappe.db.table_exists("tabZoho Books Project Mapping"):
		return
	rows = frappe.db.sql(
		"SELECT erpnext_project, zoho_project_id, zoho_project_name FROM `tabZoho Books Project Mapping`",
		as_dict=True,
	)
	for row in rows:
		_upsert("Project", row.erpnext_project, row.zoho_project_id, row.zoho_project_name or "")
	frappe.logger().info(f"Migrated {len(rows)} project mapping(s)")


def _migrate_tasks():
	if not frappe.db.has_column("Task", "zoho_task_id"):
		return
	rows = frappe.db.sql(
		"SELECT name, zoho_task_id FROM `tabTask` WHERE zoho_task_id IS NOT NULL AND zoho_task_id != ''",
		as_dict=True,
	)
	for row in rows:
		_upsert("Task", row.name, row.zoho_task_id)
	frappe.logger().info(f"Migrated {len(rows)} task mapping(s)")


def _migrate_timesheet_entries():
	if not frappe.db.has_column("Timesheet Detail", "zoho_entry_id"):
		return
	rows = frappe.db.sql(
		"SELECT name, zoho_entry_id FROM `tabTimesheet Detail` WHERE zoho_entry_id IS NOT NULL AND zoho_entry_id != ''",
		as_dict=True,
	)
	for row in rows:
		_upsert("Timesheet Detail", row.name, row.zoho_entry_id)
	frappe.logger().info(f"Migrated {len(rows)} timesheet entry mapping(s)")
