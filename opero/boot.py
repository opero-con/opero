"""Session boot additions."""

from __future__ import annotations

from opero import entity
from opero.workspace_sidebar import filter_hidden_workspaces


def boot_session(bootinfo):
	"""Publish the entity the user is working in and drop hidden workspaces.

	Forms compare it with each document's entity to flag cross-entity work.
	Sending it at boot keeps that check off the per-form request path; changing
	Session Defaults reloads the desk, so it does not go stale.
	"""
	bootinfo.opero_session_entity = entity.describe_company(entity.get_session_company())
	if bootinfo.get("workspaces"):
		bootinfo.workspaces["pages"] = filter_hidden_workspaces(bootinfo.workspaces["pages"])
