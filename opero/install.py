"""Install hooks."""

from __future__ import annotations

from opero.patches.v0_3 import add_company_display_name


def after_install():
	"""Create schema that patches add on upgrade.

	A fresh install marks every patch as done without running it, so fields the
	code reads unconditionally must also be created here.
	"""
	add_company_display_name.execute()
