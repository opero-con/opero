"""Allocation alerts show human-readable, escaped Task subjects."""

from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from opero.events import timesheet


class TestTimesheetTaskLabels(TestCase):
	def test_allocation_alert_uses_task_subject(self):
		for subject, expected in [
			("Field survey", "Field survey"),
			("Survey <East>", "Survey &lt;East&gt;"),
			(None, "TASK-2026-00001"),
		]:
			with self.subTest(subject=subject):
				doc = MagicMock(employee="EMP-1", name="TS-1", parent_project="PROJ-1")
				doc.time_logs = [
					frappe._dict(task="TASK-2026-00001", from_time="2026-10-08 08:00:00", hours=7)
				]
				with (
					patch.object(timesheet, "frappe") as api,
					patch.object(timesheet, "get_monthly_balances", return_value=({}, {})),
					patch.object(timesheet, "_pm_name_from_parent_project", return_value="Pato"),
				):
					api.db.get_value.return_value = subject
					api.throw.side_effect = ValueError
					with self.assertRaises(ValueError):
						timesheet._validate_allocated_hours(doc)
					message = api.throw.call_args.args[0]
					self.assertIn(f"<b>{expected}</b>", message)
					if subject:
						self.assertNotIn("TASK-2026-00001", message)
