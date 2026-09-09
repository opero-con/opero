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
				"Home Hero": "Home Hero",
				"Home About": "Home About",
				"Home Pillars": "Home Pillars",
				"Home Impacts": "Home Impacts",
				"Home Projects": "Home Projects",
				"Home Partners": "Home Partners",
				"Team": "Team Member",
				"Enterprises": "Enterprise",
				"Publications": "Publication",
				"Privacy policy": "Privacy policy",
				"Deploy Center": "Deploy Center",
				"Settings": "Site Settings",
			},
		)
		self.assertNotIn("Website Settings", links.values())
		self.assertNotIn("Office", links.values())

		shortcuts = {row.label: row.link_to for row in doc.shortcuts}
		self.assertEqual(shortcuts["Deploy Center"], "Deploy Center")
		self.assertEqual(shortcuts["Settings"], "Site Settings")
		self.assertEqual(shortcuts["Home Hero"], "Home Hero")
		self.assertEqual(
			set(shortcuts),
			{
				"Deploy Center",
				"Settings",
				"Home Hero",
				"Team",
				"Enterprises",
				"Publications",
				"Privacy policy",
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
			"Home Hero",
			"Home About",
			"Home Pillars",
			"Home Impacts",
			"Home Projects",
			"Home Partners",
			"Team Member",
			"Enterprise",
			"Publication",
			"Privacy policy",
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
		for doctype in ("Home Page", "Privacy policy", "Site Settings"):
			self.assertFalse(frappe.get_meta(doctype).has_field("show_on_website"), doctype)
		self.assertTrue(frappe.get_meta("Publication").has_field("show_on_website"))
		self.assertTrue(frappe.get_meta("Team Member").has_field("show_on_website"))
		self.assertTrue(frappe.get_meta("Enterprise").has_field("show_on_website"))
		self.assertTrue(frappe.get_meta("Partner").has_field("show_on_website"))
		self.assertTrue(frappe.get_meta("Enterprise").has_field("website_status"))
		self.assertEqual(
			frappe.get_meta("Enterprise").get_field("status").options.split("\n"),
			["Identified", "Onboarded", "Active Support", "Graduated", "Dormant"],
		)
		self.assertEqual(
			frappe.get_meta("Enterprise").get_field("website_status").options.split("\n"),
			["Draft", "To deploy", "Published", "To unpublish", "Unpublished"],
		)

	def test_lone_section_children_do_not_repeat_the_section_title(self):
		cases = (
			("Publication", "section_topics", "topics", "Topics"),
			("Publication", "section_body", "body", "Body"),
			("Site Settings", "section_offices", "offices", "Address"),
		)
		for doctype, section, child, title in cases:
			meta = frappe.get_meta(doctype)
			self.assertFalse(meta.get_field(section).label, f"{doctype}.{section}")
			self.assertEqual(meta.get_field(child).label, title, f"{doctype}.{child}")

	def test_publication_show_on_website_has_no_deploy_helper(self):
		field = frappe.get_meta("Publication").get_field("show_on_website")
		self.assertFalse(field.description)
