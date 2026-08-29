"""Deploy Log records a deploy, not a publish: deployed_on/deployed_by replace published_on/published_by."""

from __future__ import annotations

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doc("opero_site", "doctype", "deploy_log")

	if frappe.db.has_column("Deploy Log", "published_on"):
		rename_field("Deploy Log", "published_on", "deployed_on")
	if frappe.db.has_column("Deploy Log", "published_by"):
		rename_field("Deploy Log", "published_by", "deployed_by")
