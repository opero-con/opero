"""Website view counts: how many times each published article has been opened.

The public site calls these with its Cubenet API key. `views` lives on the
Publication record so editors can read it, but it is not exported to
opero-content: `Publication.to_site_frontmatter` lists its fields explicitly.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, cstr

from opero.opero_site.publish_status import PUBLISHED

MAX_SLUG = 140


@frappe.whitelist(methods=["POST"])
def record_view(slug: str) -> dict:
	"""Add one view to a published publication and return the new total."""
	_require_user()

	name = cstr(slug).replace("\x00", "").strip()[:MAX_SLUG]
	if not name or frappe.db.get_value("Publication", name, "status") != PUBLISHED:
		frappe.throw(_("Unknown publication."), frappe.DoesNotExistError)

	# A single UPDATE keeps the increment atomic. Saving the document instead
	# would bump `modified`, add a Version row and could disturb publishing.
	table = frappe.qb.DocType("Publication")
	frappe.qb.update(table).set(table.views, table.views + 1).where(table.name == name).run()
	return {"views": cint(frappe.db.get_value("Publication", name, "views"))}


@frappe.whitelist(methods=["GET"])
def get_views() -> dict:
	"""Return the view count of every published publication, by slug."""
	_require_user()

	rows = frappe.get_all("Publication", filters={"status": PUBLISHED}, fields=["name", "views"])
	return {"views": {row.name: cint(row.views) for row in rows}}


def _require_user() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Not permitted"), frappe.PermissionError)
