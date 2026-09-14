"""Row permissions for timesheet SQL reports, including access through sharing."""

from frappe.model.db_query import DatabaseQuery


def match_conditions(doctype, alias):
	query = DatabaseQuery(doctype)
	match = query.build_match_conditions()
	# For users with access only through sharing, Frappe places the share clause
	# in query.conditions rather than in the returned match expression.
	conditions = [condition for condition in [*query.conditions, match] if condition]
	if not conditions:
		return ""
	return (" AND (" + ") AND (".join(conditions) + ")").replace(f"`tab{doctype}`", alias).replace("%", "%%")
