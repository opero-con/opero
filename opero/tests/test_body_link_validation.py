"""Body links can be checked without a database or a running Desk."""

import unittest
from unittest.mock import patch

from opero.opero_site import body_html


def reject_link(message, **kwargs):
	raise ValueError(message)


class TestBodyLinks(unittest.TestCase):
	def setUp(self):
		self.translations = patch.object(body_html, "_", lambda value: value)
		self.translations.start()
		self.utils_translations = patch("opero.opero_site.utils._", lambda value: value)
		self.utils_translations.start()
		self.addCleanup(self.utils_translations.stop)
		self.addCleanup(self.translations.stop)
		self.messages = patch("frappe.throw", side_effect=reject_link)
		self.messages.start()
		self.addCleanup(self.messages.stop)

	def test_missing_scheme_is_completed_for_web_addresses(self):
		self.assertEqual(
			body_html.normalize_body_html('<p><a href="www.example.com/report">Read report</a></p>'),
			'<p><a href="https://www.example.com/report">Read report</a></p>',
		)

	def test_invalid_link_identifies_body_text_and_action(self):
		with self.assertRaisesRegex(ValueError, "Read report.*Edit this link in Body"):
			body_html.normalize_body_html('<p><a href="report.pdf">Read report</a></p>')

	def test_unsafe_link_is_rejected(self):
		with self.assertRaises(ValueError):
			body_html.normalize_body_html('<p><a href="javascript:alert(1)">Read report</a></p>')

	def test_existing_site_and_private_attachment_paths_survive(self):
		for href in [
			"/private/files/report.pdf",
			"/files/report.pdf",
			"/media/report.pdf",
			"https://example.com/report",
		]:
			html = f'<p><a href="{href}">Read report</a></p>'
			self.assertEqual(body_html.normalize_body_html(html), html)
