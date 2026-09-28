"""Session boot additions."""

from __future__ import annotations

from opero import entity
from opero.workspace_sidebar import filter_hidden_workspaces


def boot_session(bootinfo):
	"""Publish the signed-in user's own entity and drop hidden workspaces.

	Forms use the entity to tell ordinary work apart from cross-entity work.
	Sending it at boot keeps that check off the per-form request path.
	"""
	bootinfo.opero_home_company = entity.get_home_company()
	bootinfo.allowed_workspaces = filter_hidden_workspaces(bootinfo.allowed_workspaces or [])
