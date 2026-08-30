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
				"Home Page": "Home Page",
				"Team": "Team Member",
				"Publications": "Publication",
				"Privacy": "Privacy",
				"Deploy Center": "Deploy Center",
				"Settings": "Site Settings",
			},
		)
		self.assertNotIn("Website Settings", links.values())
		self.assertNotIn("Office", links.values())

		shortcuts = {row.label: row.link_to for row in doc.shortcuts}
		self.assertEqual(shortcuts["Deploy Center"], "Deploy Center")
		self.assertEqual(shortcuts["Settings"], "Site Settings")
		self.assertEqual(
			set(shortcuts),
			{"Deploy Center", "Settings", "Home Page", "Team", "Publications", "Privacy"},
		)
		self.assertEqual(
			{row.role for row in doc.roles},
			{"System Manager", "Website Manager"},
		)

	def test_website_manager_can_read_site_doctypes(self):
		doctypes = [
			"Home Page",
			"Team Member",
			"Publication",
			"Privacy",
			"Deploy Center",
			"Site Settings",
		]
		for doctype in doctypes:
			roles = {
				row.role for row in frappe.get_meta(doctype).permissions if row.read
			}
			self.assertIn("System Manager", roles, doctype)
			self.assertIn("Website Manager", roles, doctype)
