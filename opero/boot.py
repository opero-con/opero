"""Session boot additions."""

from __future__ import annotations

from opero import entity


def boot_session(bootinfo):
	"""Publish the signed-in user's own entity.

	Forms use it to tell ordinary work apart from cross-entity work. Sending it
	at boot keeps that check off the per-form request path.
	"""
	bootinfo.opero_home_company = entity.get_home_company()
