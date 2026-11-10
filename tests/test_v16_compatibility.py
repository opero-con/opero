"""Run with the v16 Python environment; no database or outbound services needed."""

import importlib
import unittest
from unittest.mock import patch

import frappe
from frappe.desk import desktop

from opero import boot, hooks, workspace_sidebar


class TestV16Compatibility(unittest.TestCase):
	def test_newsletter_controller_and_public_endpoints(self):
		from newsletter.newsletter.doctype.newsletter.newsletter import Newsletter

		from opero.mailing.overrides import MailingNewsletter

		self.assertTrue(issubclass(MailingNewsletter, Newsletter))
		for prefix in (
			"newsletter.newsletter.doctype.newsletter.newsletter",
			"frappe.email.doctype.newsletter.newsletter",
		):
			self.assertEqual(
				hooks.override_whitelisted_methods[f"{prefix}.subscribe"],
				"opero.mailing.confirmation.subscribe",
			)
			self.assertEqual(
				hooks.override_whitelisted_methods[f"{prefix}.confirm_subscription"],
				"opero.mailing.confirmation.legacy_confirmation",
			)
		self.assertIn("newsletter", hooks.required_apps)

	def test_signup_uses_newsletter_default_group(self):
		from opero.mailing import confirmation

		with (
			patch(
				"newsletter.newsletter.doctype.newsletter.newsletter.get_default_email_group",
				return_value="Default",
			),
			patch.object(confirmation, "frappe") as framework,
			patch.object(confirmation, "_", side_effect=lambda text: text),
			patch.object(confirmation, "ensure_member", return_value=frappe._dict(unsubscribed=0)) as member,
		):
			framework.db.exists.return_value = True
			confirmation.subscribe.__wrapped__("person@example.com")
		member.assert_called_once_with("Default", "person@example.com")

	def test_workspace_filter_is_per_user_and_preserves_framework_cache(self):
		pages = [
			frappe._dict(name="Website", public=1, is_hidden=1),
			frappe._dict(name="Site Content", public=1, is_hidden=0),
			frappe._dict(name="Mine", public=0, is_hidden=1),
		]
		payload = {"pages": pages, "has_access": True, "has_create_access": True}
		with patch.object(desktop, "get_workspaces", return_value=payload) as original:
			original._opero_workspace_filter = False
			workspace_sidebar.apply_workspace_filter()
			wrapped = desktop.get_workspaces
			workspace_sidebar.apply_workspace_filter()
			self.assertIs(desktop.get_workspaces, wrapped)
			with patch.object(frappe, "get_roles", return_value=["Workspace Manager"]):
				self.assertEqual(
					[p.name for p in desktop.get_workspaces()["pages"]], ["Site Content", "Mine"]
				)
			with patch.object(frappe, "get_roles", return_value=["System Manager", "Workspace Manager"]):
				self.assertEqual(desktop.get_workspaces()["pages"], pages)
			self.assertEqual(len(payload["pages"]), 3)
			self.assertEqual(original.call_count, 2)

	def test_v16_boot_filters_native_workspaces(self):
		payload = frappe._dict(workspaces={"pages": [frappe._dict(name="Website", public=1, is_hidden=1)]})
		with (
			patch.object(boot.entity, "get_session_company", return_value="Opero"),
			patch.object(boot.entity, "describe_company", side_effect=lambda company: {"company": company}),
			patch.object(frappe, "get_roles", return_value=["Workspace Manager"]),
		):
			boot.boot_session(payload)
		self.assertEqual(payload.workspaces["pages"], [])
		self.assertEqual(payload.opero_session_entity, {"company": "Opero"})

	def test_fresh_install_creates_company_display_name(self):
		from opero import install

		self.assertEqual(hooks.after_install, "opero.install.after_install")
		with patch.object(install.add_company_display_name, "execute") as execute:
			install.after_install()
		execute.assert_called_once_with()

	def test_all_app_modules_import(self):
		from pathlib import Path

		import opero

		root = Path(opero.__file__).parent
		for path in sorted(root.rglob("*.py")):
			if "tests" in path.parts or path.name.startswith("test_"):
				continue
			module = ".".join(("opero", *path.relative_to(root).with_suffix("").parts))
			with self.subTest(module=module):
				importlib.import_module(module.removesuffix(".__init__"))


if __name__ == "__main__":
	unittest.main()
