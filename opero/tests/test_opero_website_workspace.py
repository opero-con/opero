"""Opero Website workspace lists public-site DocTypes, not Frappe Website."""

import frappe
from frappe.tests.utils import FrappeTestCase


class TestOperoWebsiteWorkspace(FrappeTestCase):
	def test_workspace_is_top_level_and_lists_site_doctypes(self):
		doc = frappe.get_doc("Workspace", "Opero Website")
		self.assertEqual(doc.parent_page, "")
		self.assertEqual(doc.public, 1)
		self.assertEqual(doc.module, "Opero Site")
		self.assertNotEqual(doc.name, "Website")

		links = {row.label: row.link_to for row in doc.links if row.type == "Link"}
		self.assertEqual(
			links,
			{
				"Home": "Opero Site Home",
				"Team": "Opero Site Team Member",
				"Publications": "Opero Site Publication",
				"Privacy": "Opero Site Privacy",
				"Publisher": "Opero Site Publisher",
				"Settings": "Opero Site Settings",
			},
		)
		self.assertNotIn("Website Settings", links.values())
		self.assertNotIn("Opero Site Office", links.values())

		shortcuts = {row.label: row.link_to for row in doc.shortcuts}
		self.assertEqual(shortcuts["Publisher"], "Opero Site Publisher")
		self.assertEqual(shortcuts["Settings"], "Opero Site Settings")
		self.assertEqual(
			set(shortcuts),
			{"Publisher", "Settings", "Home", "Team", "Publications", "Privacy"},
		)
