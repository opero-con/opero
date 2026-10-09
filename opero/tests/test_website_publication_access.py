from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.opero_site.publish import (
	_require_document_deploy_permission,
	deploy_selected,
	preview_document_deploy,
)
from opero.patches.v0_4.add_website_publication_publisher import MODULE_PROFILE, ROLE


class TestWebsitePublicationAccess(FrappeTestCase):
	def setUp(self):
		developer_mode = patch.dict(frappe.conf, {"developer_mode": 0})
		developer_mode.start()
		self.addCleanup(developer_mode.stop)
		self.previous_user = frappe.session.user
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, self.previous_user)
		self.user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"website-access-{frappe.generate_hash(length=10)}@example.invalid",
				"first_name": "Website access test",
				"user_type": "System User",
				"send_welcome_email": 0,
				"role_profile_name": ROLE,
				"module_profile": MODULE_PROFILE,
				"default_workspace": "Site Content",
			}
		).insert(ignore_permissions=True)
		self.addCleanup(self.remove_test_user)
		frappe.set_user(self.user.name)

	def remove_test_user(self):
		frappe.set_user("Administrator")
		frappe.delete_doc("User", self.user.name, ignore_permissions=True, force=True)

	def test_effective_permissions_are_limited_to_publications(self):
		for permission in ("read", "create", "write"):
			self.assertTrue(frappe.has_permission("Publication", permission))
		for permission in ("delete", "share"):
			self.assertFalse(frappe.has_permission("Publication", permission))
		for doctype in (
			"Employee",
			"Timesheet",
			"Project",
			"Enterprise",
			"Sales Invoice",
			"Payment Entry",
			"Site Settings",
			"Deploy Center",
		):
			self.assertFalse(frappe.has_permission(doctype, "read"), doctype)
		self.assertTrue(frappe.has_permission("Publication Type", "read"))
		self.assertFalse(frappe.has_permission("Publication Type", "write"))
		blocked = {row.module for row in self.user.block_modules}
		self.assertIn("HR", blocked)
		self.assertNotIn("Opero", blocked)
		self.assertNotIn("Opero Site", blocked)

	def test_publication_deploy_requires_write_and_rejects_other_records(self):
		doc = MagicMock(doctype="Publication")
		_require_document_deploy_permission(doc)
		doc.check_permission.assert_called_once_with("write")
		doc.doctype = "Partner"
		with self.assertRaises(frappe.PermissionError):
			_require_document_deploy_permission(doc)

	def test_denied_requests_do_not_reach_repository(self):
		doc = MagicMock(doctype="Publication")
		doc.check_permission.side_effect = frappe.PermissionError
		with patch("opero.opero_site.publish.get_site_document", return_value=doc), patch(
			"opero.opero_site.publish.preview_paths"
		) as preview:
			with self.assertRaises(frappe.PermissionError):
				preview_document_deploy("Publication", "denied")
			preview.assert_not_called()
		with patch("opero.opero_site.publish.deploy_paths") as deploy:
			with self.assertRaises(frappe.ValidationError):
				deploy_selected(["content/publications/test.md"])
			deploy.assert_not_called()

	def test_publication_preview_is_scoped_to_that_document(self):
		doc = MagicMock(doctype="Publication")
		paths = ["content/publications/one-article.md"]
		with patch("opero.opero_site.publish.get_site_document", return_value=doc), patch(
			"opero.opero_site.publish.document_deploy_paths", return_value=paths
		), patch("opero.opero_site.publish.preview_paths", return_value={"files": []}) as preview:
			self.assertEqual(preview_document_deploy("Publication", "one-article"), {"files": []})
			doc.check_permission.assert_called_once_with("write")
			preview.assert_called_once_with(paths)

	def test_private_media_is_permission_checked_before_reading(self):
		from opero.opero_site.media import read_desk_file

		file = MagicMock()
		file.check_permission.side_effect = frappe.PermissionError
		with patch("opero.opero_site.media.frappe.get_doc", return_value=file), patch(
			"builtins.open"
		) as opened:
			with self.assertRaises(frappe.PermissionError):
				read_desk_file("/private/files/hr-attachment.pdf")
			file.check_permission.assert_called_once_with("read")
			opened.assert_not_called()

	def test_inbox_defaults_do_not_expose_communications(self):
		from opero.opero_site.enquiry import communication_permission_query

		communication = frappe.get_doc(
			{"doctype": "Communication", "subject": "Private enquiry", "owner": "Administrator"}
		)
		self.assertFalse(frappe.has_permission("Communication", "read", doc=communication))
		self.assertEqual(communication_permission_query(), "1=0")
		self.assertEqual(frappe.get_list("Communication", fields=["name"]), [])

	def test_mailing_defaults_do_not_expose_subscriber_data(self):
		from opero.opero_site.access import mailing_permission_query

		self.assertEqual(mailing_permission_query(), "1=0")
		for doctype in ("Email Group", "Email Group Member"):
			doc = frappe.get_doc({"doctype": doctype})
			self.assertFalse(frappe.has_permission(doctype, "read", doc=doc), doctype)
			try:
				rows = frappe.get_list(doctype, fields=["name"])
			except frappe.PermissionError:
				continue
			self.assertEqual(rows, [], doctype)

	def test_site_content_workspace_is_available_to_publisher(self):
		from frappe.desk.desktop import get_workspace_sidebar_items

		workspace = frappe.get_doc("Workspace", "Site Content")
		self.assertIn(ROLE, {row.role for row in workspace.roles})
		sidebar = get_workspace_sidebar_items()
		self.assertIn("Site Content", {row["name"] for row in sidebar["pages"]})
		self.assertIn("Opero", {row["name"] for row in sidebar["pages"]})
