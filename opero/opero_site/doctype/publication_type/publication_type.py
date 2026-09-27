import frappe
from frappe.model.document import Document
from frappe.utils import cstr

from opero.opero_site.publish_status import PUBLISHED, TO_UPDATE


class PublicationType(Document):
	def validate(self):
		self.title = cstr(self.title).strip()

	def before_rename(self, old: str, new: str, merge: bool = False):
		frappe.flags.moved_publications = frappe.get_all(
			"Publication",
			filters={"publication_type": old, "status": PUBLISHED},
			pluck="name",
		)

	def after_rename(self, old: str, new: str, merge: bool = False):
		# Rename rewrites the Link values by SQL, so queue the live files that now carry the new type.
		moved = frappe.flags.pop("moved_publications", None) or []
		if moved:
			frappe.db.set_value(
				"Publication", {"name": ["in", moved]}, "status", TO_UPDATE, update_modified=False
			)
