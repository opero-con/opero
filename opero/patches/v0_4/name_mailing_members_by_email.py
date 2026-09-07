import frappe

from opero.mailing.membership import MEMBER
from opero.mailing.overrides import readable_member_name


def execute():
	for row in frappe.get_all(MEMBER, fields=["name", "email_group", "email"], order_by="creation"):
		new_name = readable_member_name(row.email_group, row.email)
		if row.name == new_name:
			continue
		frappe.rename_doc(MEMBER, row.name, new_name, force=True)
