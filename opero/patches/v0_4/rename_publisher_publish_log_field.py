"""Deploy Center's deploy_log table field replaces the old publish_log fieldname."""

from __future__ import annotations

import frappe


def execute():
	frappe.reload_doc("opero_site", "doctype", "deploy_center")
	frappe.reload_doc("opero_site", "doctype", "deploy_log")

	if frappe.db.has_column("Deploy Log", "parentfield"):
		frappe.db.sql(
			"""
			UPDATE `tabDeploy Log`
			SET parentfield = 'deploy_log'
			WHERE parenttype = 'Deploy Center' AND parentfield = 'publish_log'
			"""
		)
