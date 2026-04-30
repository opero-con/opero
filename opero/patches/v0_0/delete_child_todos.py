import frappe


def execute():
	child_names = frappe.get_all("ToDo", filters={"custom_is_group_child": 1}, pluck="name")
	for name in child_names:
		frappe.delete_doc("ToDo", name, ignore_permissions=True, force=True)
