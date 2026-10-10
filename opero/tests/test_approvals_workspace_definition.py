"""Approval shortcuts must include the current user's open leave requests."""

import json
import unittest
from pathlib import Path


class TestApprovalsWorkspaceDefinition(unittest.TestCase):
	def test_leave_queue_targets_open_applications_for_current_approver(self):
		path = Path(__file__).parents[1] / "opero/workspace/approvals/approvals.json"
		workspace = json.loads(path.read_text())
		rows = [row for row in workspace["shortcuts"] if row["label"] == "Leave Applications"]
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["link_to"], "Leave Application")
		self.assertEqual(rows[0]["doc_view"], "List")
		self.assertEqual(rows[0]["format"], "{} to approve")
		self.assertEqual(
			rows[0]["stats_filter"],
			'[["Leave Application","status","=","Open"],'
			'["Leave Application","leave_approver","=",frappe.session.user],'
			'["Leave Application","docstatus","=",0]]',
		)
		blocks = json.loads(workspace["content"])
		leave = [b for b in blocks if b["data"].get("shortcut_name") == "Leave Applications"]
		self.assertEqual(len(leave), 1)
		self.assertEqual(leave[0]["data"]["col"], 4)
