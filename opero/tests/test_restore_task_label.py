"""The restore_task_label patch removes the "Project Task" naming."""

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.patches.v0_4 import restore_task_label


class TestRestoreTaskLabel(FrappeTestCase):
	def test_patch_drops_translation_and_relabels(self):
		frappe.get_doc(
			{
				"doctype": "Translation",
				"language": "en",
				"source_text": "Task",
				"translated_text": "Project Task",
			}
		).insert(ignore_permissions=True)
		for name in restore_task_label.FIELD_LABELS:
			if frappe.db.exists("Custom Field", name):
				frappe.db.set_value("Custom Field", name, "label", "Project Task Label")
		workspace = frappe.get_all("Workspace", filters={"public": 1}, pluck="name", limit=1)[0]
		link = frappe.get_doc(
			{
				"doctype": "Workspace Link",
				"parent": workspace,
				"parenttype": "Workspace",
				"parentfield": "links",
				"type": "Link",
				"link_type": "DocType",
				"link_to": "Task",
				"label": "Project Task List",
			}
		)
		link.db_insert()

		restore_task_label.execute()

		self.assertFalse(
			frappe.db.exists("Translation", {"source_text": "Task", "translated_text": "Project Task"})
		)
		for name, label in restore_task_label.FIELD_LABELS.items():
			if frappe.db.exists("Custom Field", name):
				self.assertEqual(frappe.db.get_value("Custom Field", name, "label"), label)
		self.assertEqual(frappe.db.get_value("Workspace Link", link.name, "label"), "Task List")
