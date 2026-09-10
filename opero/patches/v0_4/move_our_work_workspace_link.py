"""Keep Our Work in the Opero Website workspace's Other Content group."""

from __future__ import annotations

import frappe


def execute():
	frappe.reload_doc("opero_site", "workspace", "opero_website", force=True)
