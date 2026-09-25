"""Regression: publications saved before the auto-crop feature shipped get a
computed cover position without anyone resaving them."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file
from PIL import Image, ImageDraw

from opero.opero_site.cover_focal_point import compute_cover_framing
from opero.patches.v0_4.backfill_publication_cover_position import execute
from opero.tests.test_opero_site_content import _png_bytes


class TestBackfillPublicationCoverPositionPatch(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Publication")

	def test_execute_fills_in_a_missing_cover_position(self):
		canvas = Image.new("L", (400, 160), 255)
		draw = ImageDraw.Draw(canvas)
		for x in range(350, 400, 4):
			draw.line([(x, 0), (x, 160)], fill=0, width=2)
		content = _png_bytes(canvas)

		doc = self._legacy_publication_with_cover("Pre-existing Cover", content)

		execute()

		self.assertEqual(
			tuple(frappe.db.get_value("Publication", doc.name, ["cover_fit", "cover_position"])),
			compute_cover_framing(content),
		)

	def test_execute_does_not_overwrite_an_existing_cover_position(self):
		doc = self._legacy_publication_with_cover("Already Tuned", b"fake-png-bytes")
		frappe.db.set_value("Publication", doc.name, "cover_position", "left center")

		execute()

		self.assertEqual(frappe.db.get_value("Publication", doc.name, "cover_position"), "left center")

	def test_execute_is_a_no_op_when_nothing_needs_backfilling(self):
		execute()

	def _legacy_publication_with_cover(self, title: str, content: bytes):
		doc = frappe.get_doc(
			{
				"doctype": "Publication",
				"title": title,
				"published_on": "2025-04-01",
				"publication_type": "Digest",
				"summary": "Saved before the auto-crop feature shipped.",
			}
		).insert(ignore_permissions=True)
		file_doc = save_file("legacy-cover.png", content, "Publication", doc.name, is_private=0)
		# `Publication.validate()` would compute cover_position on a normal save; write
		# straight to the database to reproduce data saved before that hook existed.
		frappe.db.set_value("Publication", doc.name, "cover", file_doc.file_url)
		frappe.db.set_value("Publication", doc.name, "cover_position", "")
		return doc
