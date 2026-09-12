"""Opero Website workspace lists public-site DocTypes, not Frappe Website."""

import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.patches.v0_4 import rename_home_section_doctypes


class TestOperoWebsiteWorkspace(FrappeTestCase):
	def test_home_section_rename_replaces_synced_destination(self):
		with (
			patch.object(rename_home_section_doctypes, "RENAMES", (("Home Hero", "Hero"),)),
			patch.object(rename_home_section_doctypes.frappe.db, "exists", side_effect=(True, True)),
			patch.object(rename_home_section_doctypes.frappe, "delete_doc") as delete_doc,
			patch.object(rename_home_section_doctypes.frappe, "rename_doc") as rename_doc,
			patch.object(rename_home_section_doctypes.frappe, "reload_doc") as reload_doc,
		):
			rename_home_section_doctypes.execute()

		delete_doc.assert_called_once_with("DocType", "Hero", force=True, ignore_permissions=True)
		rename_doc.assert_called_once_with("DocType", "Home Hero", "Hero", force=True)
		reload_doc.assert_any_call("opero_site", "doctype", "hero", force=True)

	def test_workspace_is_top_level_and_lists_site_doctypes(self):
		doc = frappe.get_doc("Workspace", "Opero Website")
		self.assertEqual(doc.parent_page, "")
		self.assertEqual(doc.public, 1)
		self.assertEqual(doc.module, "Opero Site")
		self.assertNotEqual(doc.name, "Website")

		links = {row.label: row.link_to for row in doc.links if row.type == "Link"}
		card_breaks = [row.label for row in doc.links if row.type == "Card Break"]
		self.assertEqual(card_breaks, ["Home Page", "Other Content", "Setup"])
		self.assertEqual(
			[row.link_count for row in doc.links if row.type == "Card Break"],
			[4, 5, 2],
		)
		cards = [block["data"]["card_name"] for block in json.loads(doc.content) if block["type"] == "card"]
		self.assertEqual(cards, ["Home Page", "Other Content", "Setup"])
		self.assertEqual(
			links,
			{
				"Hero": "Hero",
				"About": "About",
				"Impacts": "Impacts",
				"Our Work": "Our Work",
				"Partners": "Partners",
				"Team": "Employee",
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
		self.assertEqual(
			set(shortcuts),
			{
				"Team",
				"Enterprises",
				"Publications",
				"Website Enquiries",
			},
		)
		enquiries = next(row for row in doc.shortcuts if row.label == "Website Enquiries")
		team = next(row for row in doc.shortcuts if row.label == "Team")
		enterprises = next(row for row in doc.links if row.label == "Enterprises")
		self.assertEqual(enterprises.link_type, "DocType")
		self.assertEqual(enterprises.link_to, "Enterprise")
		self.assertEqual(enquiries.link_to, "Communication")
		self.assertEqual(enquiries.doc_view, "List")
		self.assertEqual(enquiries.stats_filter, '{"custom_source":"Website"}')
		self.assertEqual(team.link_to, "Employee")
		self.assertEqual(team.doc_view, "List")
		self.assertEqual(team.stats_filter, '{"show_on_website":1}')
		self.assertEqual(
			{row.role for row in doc.roles},
			{"System Manager", "Website Manager"},
		)

	def test_website_manager_can_read_site_doctypes(self):
		doctypes = [
			"Home Page",
			"Hero",
			"About",
			"Impacts",
			"Our Work",
			"Partners",
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

		personnel_roles = {
			row.role for row in frappe.get_meta("Employee").permissions if row.read
		}
		self.assertIn("HR User", personnel_roles)
		self.assertNotIn("Website Manager", personnel_roles)

	def test_always_on_site_singles_have_no_show_on_website(self):
		for doctype in ("Home Page", "Privacy policy", "Site Settings"):
			self.assertFalse(frappe.get_meta(doctype).has_field("show_on_website"), doctype)
		self.assertTrue(frappe.get_meta("Publication").has_field("show_on_website"))
		self.assertTrue(frappe.get_meta("Employee").has_field("show_on_website"))
		self.assertTrue(frappe.get_meta("Employee").has_field("website_status"))
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
