import frappe

from opero.opero_site.cover_focal_point import compute_cover_focal_point
from opero.opero_site.media import desk_file_url, read_desk_file


def execute():
	frappe.reload_doc("opero_site", "doctype", "publication")

	if not frappe.db.has_column("Publication", "cover_position"):
		return

	rows = frappe.get_all(
		"Publication",
		filters={"cover": ["is", "set"], "cover_position": ["in", ("", None)]},
		fields=["name", "cover"],
	)
	for row in rows:
		_backfill(row.name, row.cover)


def _backfill(name: str, cover: str) -> None:
	file_url = desk_file_url(cover)
	if not file_url:
		return
	try:
		position = compute_cover_focal_point(read_desk_file(file_url))
	except (OSError, ValueError):
		frappe.log_error(title="Cover focal point backfill")
		return
	frappe.db.set_value("Publication", name, "cover_position", position, update_modified=False)
