"""Keep hidden workspaces out of staff navigation on Frappe v16.

Most Opero staff are Workspace Managers. Only System Managers should also see
hidden public workspaces. Apply this before Frappe builds navigation from its
request-cached workspace list; filtering boot alone leaves sidebar links behind.
"""

from __future__ import annotations

from functools import wraps

import frappe
from frappe.desk import desktop


def apply_workspace_filter():
	"""Wrap the native workspace provider once per process, retaining its cache."""
	original = desktop.get_workspaces
	if getattr(original, "_opero_workspace_filter", False):
		return

	@wraps(original)
	def get_workspaces(*args, **kwargs):
		result = original(*args, **kwargs)
		return {**result, "pages": filter_hidden_workspaces(result["pages"])}

	get_workspaces._opero_workspace_filter = True
	desktop.get_workspaces = get_workspaces


def filter_hidden_workspaces(pages):
	if "System Manager" in frappe.get_roles():
		return pages
	return [page for page in pages if not (page.get("public") and page.get("is_hidden"))]
