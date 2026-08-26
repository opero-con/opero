"""Opero Website workspace lists public-site DocTypes, not Frappe Website."""

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.patches.v0_4.rename_opero_site_doctypes import RENAMES


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
				"Home": "Site Home",
				"Team": "Site Team Member",
				"Publications": "Site Publication",
				"Privacy": "Site Privacy",
				"Settings": "Site Settings",
			},
		)
		self.assertNotIn("Website Settings", links.values())
		self.assertNotIn("Site Office", links.values())

		shortcuts = {row.label: row.link_to for row in doc.shortcuts}
		self.assertEqual(shortcuts["Settings"], "Site Settings")
		self.assertEqual(set(shortcuts), {"Settings", "Home", "Team", "Publications", "Privacy"})

	def test_site_doctype_names_drop_opero_prefix(self):
		names = frappe.get_all("DocType", filters={"module": "Opero Site"}, pluck="name")
		self.assertTrue(names)
		for name in names:
			self.assertTrue(name.startswith("Site "), name)
			self.assertFalse(name.startswith("Opero "), name)
		self.assertEqual(set(names), {new for _old, new in RENAMES})
		self.assertNotIn("Home", names)
		self.assertNotIn("Homepage", names)
		self.assertNotIn("Website Settings", names)
