"""Point open documents at their project's current manager."""

from __future__ import annotations

import frappe

from opero.events.project import sync_project_manager


def execute():
	for project in frappe.get_all("Project", pluck="name"):
		sync_project_manager(project)
