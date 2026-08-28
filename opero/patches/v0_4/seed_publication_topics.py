import frappe


def execute():
	if not frappe.db.table_exists("Publication Topic") or not frappe.db.table_exists("Topic"):
		return
	titles = frappe.db.sql(
		"""
		SELECT DISTINCT TRIM(topic)
		FROM `tabTopic`
		WHERE IFNULL(TRIM(topic), '') != ''
		"""
	)
	for (title,) in titles:
		if frappe.db.exists("Publication Topic", title):
			continue
		frappe.get_doc({"doctype": "Publication Topic", "title": title}).insert(
			ignore_permissions=True,
			ignore_if_duplicate=True,
		)
