import frappe
from frappe import _

from opero.mailing.confirmation import confirm, get_request

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.title = _("Confirm your Mailing Lists")
	context.token = frappe.form_dict.get("token", "")
	context.completed = False
	context.error = None
	try:
		if frappe.request.method == "POST":
			request = get_request(context.token)
			groups = [
				r.mailing_list for i, r in enumerate(request.members) if frappe.form_dict.get(f"list_{i}")
			]
			context.confirmed_count = confirm(context.token, groups)
			context.completed = True
		else:
			request = get_request(context.token)
			context.email = request.email
			context.memberships = request.members
	except frappe.ValidationError as error:
		frappe.clear_messages()
		context.error = str(error)
