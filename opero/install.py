"""Install hooks."""

from __future__ import annotations

from opero.patches.v0_3 import add_company_display_name
from opero.patches.v0_4 import (
	add_employee_website_fields,
	adopt_publish_statuses,
	use_alternative_personnel_image,
)


def after_install():
	"""Create schema that patches add on upgrade.

	A fresh install marks every patch as done without running it, so fields the
	code reads unconditionally must also be created here.
	"""
	add_company_display_name.execute()
	add_employee_website_fields.execute()
	use_alternative_personnel_image.execute()
	adopt_publish_statuses.update_employee_fields()
