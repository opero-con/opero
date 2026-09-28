"""Opero groups Approvals and Site Content in the Desk sidebar."""

import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from opero import boot, workspace_sidebar
from opero.patches.v0_4 import hide_frappe_website_workspace, nest_opero_workspaces


class TestOperoWorkspaces(FrappeTestCase):
	def test_opero_is_the_parent_of_approvals_and_site_content(self):
		opero = frappe.get_doc("Workspace", "Opero")
		self.assertEqual(opero.parent_page, "")
		self.assertEqual(opero.module, "Opero")
		self.assertEqual({row.role for row in opero.roles}, {"Desk User", "System Manager"})
		children = frappe.get_all("Workspace", filters={"parent_page": "Opero", "public": 1}, pluck="name")
		self.assertEqual(set(children), {"Approvals", "Site Content"})
		self.assertFalse(frappe.db.exists("Workspace", "Opero Website"))
		self.assertFalse(frappe.db.exists("Workspace", "ToDo Hub"))

	def test_approvals_filter_each_queue_to_the_current_pm(self):
		doc = frappe.get_doc("Workspace", "Approvals")
		self.assertEqual({row.role for row in doc.roles}, {"Desk User", "System Manager"})
		queues = {row.label: row for row in doc.shortcuts if row.format == "{} to approve"}
		expected = {
			"Timesheets": ("Timesheet", "Submitted", "custom_pm_email"),
			"Cash Advances": ("Cash Advance-Reimbursable Form", "Pending PM's Approval", "pm_email"),
			"Consultant Tasks": ("Consultant Task", "Open", "pm_email"),
			"Travel Requests": ("Travel Request", "Pending PM's Approval", "custom_pm_email"),
		}
		self.assertEqual(set(queues), set(expected))
		widths = {
			block["data"]["shortcut_name"]: block["data"]["col"]
			for block in json.loads(doc.content)
			if block["type"] == "shortcut"
		}
		# Three per row, so "N to approve" is not truncated.
		self.assertEqual({widths[label] for label in expected}, {4})
		for label, (doctype, state, pm_field) in expected.items():
			row = queues[label]
			self.assertEqual(row.link_to, doctype)
			if frappe.db.exists("DocType", doctype):
				self.assertTrue(frappe.get_meta(doctype).has_field(pm_field), doctype)
			self.assertIn(f'["{doctype}","workflow_state","=","{state}"]', row.stats_filter)
			self.assertIn(f'["{doctype}","{pm_field}","=",frappe.session.user]', row.stats_filter)

	def test_approvals_keeps_the_todo_hub_reports(self):
		doc = frappe.get_doc("Workspace", "Approvals")
		shortcuts = {row.label: row.link_to for row in doc.shortcuts}
		self.assertEqual(shortcuts["Flow Hub"], "flow-hub")
		self.assertEqual(shortcuts["My ToDos"], "ToDo Explorer")
		reports = [row.link_to for row in doc.links if row.link_type == "Report"]
		self.assertEqual(
			reports,
			[
				"ToDo Explorer",
				"ToDo Created vs Closed",
				"ToDo Assignee Load and Risk",
				"ToDo In Progress Aging",
			],
		)
		shortcut_blocks = [
			b["data"]["shortcut_name"] for b in json.loads(doc.content) if b["type"] == "shortcut"
		]
		self.assertEqual(shortcut_blocks, [row.label for row in doc.shortcuts])

	def test_patch_keeps_old_workspace_when_replacement_is_missing(self):
		with (
			patch.object(nest_opero_workspaces.frappe.db, "exists", return_value=False),
			patch.object(nest_opero_workspaces.frappe, "delete_doc") as delete_doc,
			self.assertRaises(frappe.ValidationError),
		):
			nest_opero_workspaces.execute()
		delete_doc.assert_not_called()

	def test_hidden_workspaces_show_only_to_system_and_workspace_managers(self):
		self.assertEqual(
			frappe.get_hooks("override_whitelisted_methods")[
				"frappe.desk.desktop.get_workspace_sidebar_items"
			],
			["opero.workspace_sidebar.get_workspace_sidebar_items"],
		)
		hide_frappe_website_workspace.execute()
		self.assertEqual(frappe.db.get_value("Workspace", "Website", "is_hidden"), 1)
		self.assertIn("Website", self._sidebar_for(["System Manager", "Workspace Manager"]))
		for roles in (["Website Manager"], ["Website Manager", "Workspace Manager"], ["System Manager"]):
			with self.subTest(roles=roles):
				pages = self._sidebar_for(roles)
				self.assertNotIn("Website", pages)
				self.assertIn("Site Content", pages)

	def test_boot_drops_hidden_workspaces_from_search_and_breadcrumbs(self):
		bootinfo = frappe._dict(
			allowed_workspaces=[
				frappe._dict(name="Website", public=1, is_hidden=1),
				frappe._dict(name="Site Content", public=1, is_hidden=0),
				frappe._dict(name="Mine", public=0, is_hidden=1, for_user="someone@example.com"),
			]
		)
		with self.set_user(self._user(["Workspace Manager"])):
			boot.boot_session(bootinfo)
		self.assertEqual([page.name for page in bootinfo.allowed_workspaces], ["Site Content", "Mine"])

	def _user(self, roles):
		return (
			frappe.get_doc(
				doctype="User",
				email=f"workspace-{frappe.generate_hash(length=8)}@example.com",
				first_name="Workspace test",
				send_welcome_email=0,
				roles=[{"role": role} for role in roles],
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _sidebar_for(self, roles):
		with self.set_user(self._user(roles)):
			return [page.name for page in workspace_sidebar.get_workspace_sidebar_items()["pages"]]
