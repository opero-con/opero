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
			{
				"Deploy Center",
				"Settings",
				"Home Page",
				"Team",
				"Publications",
				"Privacy",
				"Website Enquiries",
			},
		)
		enquiries = next(row for row in doc.shortcuts if row.label == "Website Enquiries")
		self.assertEqual(enquiries.link_to, "Communication")
		self.assertEqual(enquiries.doc_view, "List")
		self.assertEqual(enquiries.stats_filter, '{"custom_source":"Website"}')
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

	def test_always_on_site_singles_have_no_show_on_website(self):
		for doctype in ("Home Page", "Privacy", "Site Settings"):
			self.assertFalse(frappe.get_meta(doctype).has_field("show_on_website"), doctype)
		self.assertTrue(frappe.get_meta("Publication").has_field("show_on_website"))
		self.assertTrue(frappe.get_meta("Team Member").has_field("show_on_website"))

	def test_lone_section_children_do_not_repeat_the_section_title(self):
		cases = (
			("Publication", "section_topics", "topics", "Topics"),
			("Publication", "section_body", "body", "Body"),
			("Home Page", "section_pillars", "pillars", "Service pillars"),
			("Home Page", "section_impacts", "impacts", "Impact metrics"),
			("Home Page", "section_projects", "projects", "Projects"),
			("Home Page", "section_partners", "partners", "Partners"),
			("Site Settings", "section_offices", "offices", "Address"),
		)
		for doctype, section, child, title in cases:
			meta = frappe.get_meta(doctype)
			self.assertFalse(meta.get_field(section).label, f"{doctype}.{section}")
			self.assertEqual(meta.get_field(child).label, title, f"{doctype}.{child}")

	def test_publication_show_on_website_has_no_deploy_helper(self):
		field = frappe.get_meta("Publication").get_field("show_on_website")
		self.assertFalse(field.description)
