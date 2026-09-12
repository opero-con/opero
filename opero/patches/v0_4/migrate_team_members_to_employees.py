"""Move website Team Member profiles onto matching Employee records."""

import frappe


FIELDS = (
	"role", "slug", "sort_order", "show_on_website", "portrait",
	"linkedin",
)


def execute():
	if not frappe.db.exists("DocType", "Team Member"):
		return
	matches = get_employee_matches()
	for team_member, employee in matches:
		migrate_profile(team_member, employee)
	for row in frappe.get_all("Team Member", pluck="name"):
		frappe.delete_doc("Team Member", row, force=True, ignore_permissions=True)
	frappe.delete_doc("DocType", "Team Member", force=True, ignore_permissions=True)
	frappe.db.sql(
		"UPDATE `tabWorkspace Link` SET link_to = 'Employee' WHERE link_to = 'Team Member' AND link_type = 'DocType'"
	)
	frappe.db.sql(
		"UPDATE `tabWorkspace Shortcut` SET link_to = 'Employee' WHERE link_to = 'Team Member' AND `type` = 'DocType'"
	)


def get_employee_matches():
	matches = []
	issues = []
	for row in frappe.get_all("Team Member", fields=["name", "member_name"]):
		employees = frappe.get_all("Employee", filters={"employee_name": row.member_name}, pluck="name")
		if not employees:
			issues.append(f"no Employee matches '{row.member_name}'")
			continue
		if len(employees) > 1:
			issues.append(f"multiple Employees are named '{row.member_name}'")
			continue
		matches.append((row.name, employees[0]))
	if issues:
		frappe.throw("Resolve Team Member migration issues: " + "; ".join(issues))
	return matches


def migrate_profile(team_member, employee):
	old = frappe.get_doc("Team Member", team_member)
	new = frappe.get_doc("Employee", employee)
	for field in FIELDS:
		new.set(field, old.get(field))
	new.use_employee_image = 0
	new.website_status = old.status
	new.save(ignore_permissions=True)
