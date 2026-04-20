# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ZohoBooksSettings(Document):
	def validate(self):
		if self.enabled:
			if not self.client_id:
				frappe.throw("Client ID is required when Zoho Books integration is enabled")
			if not self.client_secret:
				frappe.throw("Client Secret is required when Zoho Books integration is enabled")
			if not self.organization_id:
				frappe.throw("Organization ID is required when Zoho Books integration is enabled")

	def on_update(self):
		for row in self.project_mapping or []:
			if row.erpnext_project and row.zoho_project_id:
				frappe.db.set_value("Project", row.erpnext_project, "zoho_project_id", row.zoho_project_id)
