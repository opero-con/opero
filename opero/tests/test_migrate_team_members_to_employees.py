"""Migration safeguards for replacing Team Member with Employee."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.patches.v0_4.migrate_team_members_to_employees import (
	FIELDS,
	get_employee_matches,
	migrate_profile,
)


class TestMigrateTeamMembersToEmployees(FrappeTestCase):
	@patch("opero.patches.v0_4.migrate_team_members_to_employees.frappe.get_all")
	def test_preflight_rejects_missing_employee(self, get_all):
		get_all.side_effect = [[SimpleNamespace(name="TM-1", member_name="Missing Person")], []]
		with self.assertRaisesRegex(frappe.ValidationError, "no Employee matches 'Missing Person'"):
			get_employee_matches()

	@patch("opero.patches.v0_4.migrate_team_members_to_employees.frappe.get_all")
	def test_preflight_rejects_ambiguous_employee_name(self, get_all):
		get_all.side_effect = [
			[SimpleNamespace(name="TM-1", member_name="Shared Name")],
			["EMP-1", "EMP-2"],
		]
		with self.assertRaisesRegex(frappe.ValidationError, "multiple Employees are named 'Shared Name'"):
			get_employee_matches()

	@patch("opero.patches.v0_4.migrate_team_members_to_employees.frappe.get_doc")
	def test_profile_fields_move_without_changing_hr_status(self, get_doc):
		values = {field: f"value-{field}" for field in FIELDS}
		old = SimpleNamespace(status="Published", get=values.get)
		new = MagicMock(status="Active")
		get_doc.side_effect = [old, new]

		migrate_profile("TM-1", "EMP-1")

		for field, value in values.items():
			new.set.assert_any_call(field, value)
		self.assertEqual(new.website_status, "Published")
		self.assertEqual(new.status, "Active")
		self.assertEqual(new.use_employee_image, 0)
		new.save.assert_called_once_with(ignore_permissions=True)
