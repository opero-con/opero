"""Remove single-document entries from the Opero Website shortcuts."""

from __future__ import annotations

import frappe


def execute():
	frappe.reload_doc("opero_site", "workspace", "opero_website", force=True)
