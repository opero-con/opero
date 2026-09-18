"""Regression coverage for monthly balances, report dates and accounting retries."""

from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from opero import zoho_books
from opero.events import timesheet
from opero.opero.report.dynamic_timesheet.dynamic_timesheet import execute as dynamic_report
from opero.opero.report.used_hrs_summary.used_hrs_summary import execute as used_report


class TestTimesheetBalances(FrappeTestCase):
	def test_allocated_hours_is_not_a_grid_column(self):
		self.assertFalse(frappe.get_meta("Timesheet Detail").get_field("custom_a_hrs").in_list_view)

	def setUp(self):
		self.previous_user = frappe.session.user
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, self.previous_user)
		self.employee = self._record(
			"Employee", first_name="Timesheet regression", employee_name="Timesheet regression"
		)
		self.project = self._record(
			"Project", project_name="Timesheet regression " + frappe.generate_hash(length=12)
		)
		self.task = self._record("Task", subject="Timesheet regression", project=self.project)
		ttd = self._record(
			"Task Time Distribution", personnel=self.employee, project_task=self.task, project=self.project
		)
		for month, hours in (("Jan 2026", 10), ("Feb 2026", 20), ("Jan 2025", 30)):
			self._record(
				"Task Time Distribution Spread",
				parent=ttd,
				parenttype="Task Time Distribution",
				parentfield="task_time_distribution_spread",
				month=month,
				time_spread=hours,
			)

	def _record(self, doctype, **values):
		doc = frappe.get_doc(
			dict(doctype=doctype, name="ts-test-" + frappe.generate_hash(length=12), **values)
		)
		doc.db_insert()
		return doc.name

	def _sheet(self, status, entries):
		name = self._record(
			"Timesheet",
			employee=self.employee,
			employee_name="Timesheet regression",
			parent_project=self.project,
			docstatus=status,
			start_date="2026-01-01",
			total_hours=sum(hours for _, hours in entries),
		)
		for date, hours in entries:
			self._record(
				"Timesheet Detail",
				parent=name,
				parenttype="Timesheet",
				parentfield="time_logs",
				task=self.task,
				project=self.project,
				from_time=date + " 09:00:00",
				hours=hours,
			)
		return name

	def _draft(self, hours, date="2026-01-10", name=None):
		return frappe._dict(
			name=name,
			employee=self.employee,
			parent_project=self.project,
			time_logs=[
				frappe._dict(task=self.task, from_time=date + " 09:00:00", hours=h, idx=i + 1, custom_a_hrs=0)
				for i, h in enumerate(hours)
			],
		)

	def test_multiple_rows_cannot_each_spend_the_full_allocation(self):
		with self.assertRaises(frappe.ValidationError):
			timesheet._validate_allocated_hours(self._draft([6, 6]))

	def test_submitted_usage_counts_but_drafts_and_cancelled_do_not(self):
		self._sheet(1, [("2026-01-02", 6)])
		self._sheet(0, [("2026-01-03", 100)])
		self._sheet(2, [("2026-01-04", 100)])
		timesheet._validate_allocated_hours(self._draft([4]))
		with self.assertRaises(frappe.ValidationError):
			timesheet._validate_allocated_hours(self._draft([5]))

	def test_current_document_is_excluded_and_months_are_independent(self):
		name = self._sheet(1, [("2026-01-02", 10)])
		doc = self._draft([10], name=name)
		timesheet._validate_allocated_hours(doc)
		self.assertEqual(doc.time_logs[0].custom_a_hrs, 10)
		timesheet._validate_allocated_hours(self._draft([20], date="2026-02-02"))
		with self.assertRaises(frappe.ValidationError):
			timesheet._validate_allocated_hours(self._draft([21], date="2026-02-02"))

	def test_missing_month_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			timesheet._validate_allocated_hours(self._draft([1], date="2026-03-02"))

	def test_cross_midnight_never_moves_the_start(self):
		doc = self._draft([2])
		doc.time_logs[0].from_time = "2026-01-31 23:00:00"
		with self.assertRaises(frappe.ValidationError):
			timesheet._anti_spill(doc)
		self.assertEqual(doc.time_logs[0].from_time, "2026-01-31 23:00:00")
		doc.time_logs[0].hours = 1
		timesheet._anti_spill(doc)

	def test_reports_use_detail_dates_and_exclude_non_submitted(self):
		self._sheet(1, [("2026-01-02", 3), ("2026-02-02", 7), ("2025-01-02", 5)])
		self._sheet(0, [("2026-01-03", 100)])
		self._sheet(2, [("2026-01-04", 100)])
		columns, data = dynamic_report({"project": self.project})
		self.assertEqual(len(data), 1)
		self.assertEqual(data[0]["month_2025_01"], 5)
		self.assertEqual(data[0]["month_2026_01"], 3)
		self.assertEqual(data[0]["month_2026_02"], 7)
		_, data = used_report({"project": self.project, "year": 2026})
		self.assertEqual({row.month: row.posted_hrs for row in data}, {"January": 3, "February": 7})
		columns, data = dynamic_report(
			{"project": self.project, "from_date": "2026-02-01", "to_date": "2026-02-28"}
		)
		self.assertEqual(
			[col["fieldname"] for col in columns if col["fieldname"].startswith("month_")], ["month_2026_02"]
		)
		self.assertEqual(data[0]["month_2026_02"], 7)

	def test_server_total_has_no_thousand_document_cap(self):
		from opero.api.timesheet import get_total_spent_hours

		self._sheet(1, [("2026-01-02", 6)])
		self._sheet(2, [("2026-01-03", 100)])
		# Aggregate query, rather than transferring individual records.
		with patch("opero.api.timesheet.frappe.get_list", wraps=frappe.get_list) as query:
			self.assertEqual(get_total_spent_hours(self.employee, self.project), 6)
			self.assertTrue(
				any(
					call.kwargs.get("fields") == ["sum(total_hours) as hours"]
					for call in query.call_args_list
				)
			)

	def test_report_permissions_include_share_only_access(self):
		from opero.opero.report.timesheet_permissions import match_conditions

		query = MagicMock()
		query.conditions = ["`tabTimesheet`.`name` in ('shared')"]
		query.build_match_conditions.return_value = ""
		with patch("opero.opero.report.timesheet_permissions.DatabaseQuery", return_value=query):
			self.assertIn("ts.`name` in ('shared')", match_conditions("Timesheet", "ts"))

	def test_live_balance_preview_matches_validation(self):
		from opero.api.timesheet import get_allocation_balances

		self._sheet(1, [("2026-01-02", 3)])
		doc = self._draft([2, 4])
		balance = get_allocation_balances(self.employee, self.project, doc.time_logs)[0]
		self.assertEqual(
			(balance["allocated"], balance["submitted"], balance["current"], balance["remaining"]),
			(10, 3, 6, 1),
		)
		timesheet._validate_allocated_hours(doc)

	def test_submission_blocked_after_cutoff_day(self):
		doc = self._draft([2], date="2026-01-15")
		with patch.object(frappe, "get_roles", return_value=["Projects User"]):
			with patch.object(timesheet, "nowdate", return_value="2026-02-04"):
				with self.assertRaises(frappe.ValidationError):
					timesheet._validate_submission_cutoff(doc)
			with patch.object(timesheet, "nowdate", return_value="2026-02-03"):
				timesheet._validate_submission_cutoff(doc)

	def test_submission_cutoff_bypassed_for_projects_manager(self):
		doc = self._draft([2], date="2026-01-15")
		with patch.object(timesheet, "nowdate", return_value="2026-02-04"), patch.object(
			frappe, "get_roles", return_value=["Projects Manager"]
		):
			timesheet._validate_submission_cutoff(doc)


class TestTimesheetZoho(FrappeTestCase):
	def test_submission_only_queues_after_commit(self):
		with patch.object(zoho_books, "_get_settings", return_value=frappe._dict(enabled=1)), patch.object(
			frappe.db, "set_value"
		), patch.object(frappe, "enqueue") as enqueue:
			zoho_books.sync_timesheet_to_zoho(frappe._dict(name="test"))
			self.assertTrue(enqueue.call_args.kwargs["enqueue_after_commit"])
			self.assertEqual(enqueue.call_args.kwargs["timesheet_name"], "test")

	def test_retry_skips_mapped_entries_and_reports_failure(self):
		doc = frappe._dict(
			name="test",
			employee="employee",
			note="",
			time_logs=[frappe._dict(name="mapped", idx=1), frappe._dict(name="failed", idx=2)],
		)
		with patch.object(
			zoho_books, "_get_settings", return_value=frappe._dict(enabled=1, organization_id="org")
		), patch.object(zoho_books, "_validate_settings"), patch.object(
			zoho_books, "_get_or_refresh_token"
		), patch.object(
			zoho_books, "_get_mapping", side_effect=lambda kind, name: "remote" if name != "failed" else None
		), patch.object(
			zoho_books, "_create_time_entry", side_effect=zoho_books.ZohoBooksException("offline")
		) as create, patch.object(frappe.db, "commit"):
			with self.assertRaises(zoho_books.ZohoBooksException):
				zoho_books._sync_timesheet_entries(doc)
			self.assertEqual(create.call_count, 1)
			self.assertEqual(create.call_args.args[0].name, "failed")

	def test_uncertain_create_is_not_repeated(self):
		doc = frappe._dict(
			name="test",
			employee="employee",
			note="",
			time_logs=[frappe._dict(name="unknown", idx=1, custom_zoho_sync_uncertain=1)],
		)
		with patch.object(
			zoho_books, "_get_settings", return_value=frappe._dict(enabled=1, organization_id="org")
		), patch.object(zoho_books, "_validate_settings"), patch.object(
			zoho_books, "_get_or_refresh_token"
		), patch.object(
			zoho_books, "_get_mapping", side_effect=lambda kind, name: "user" if kind == "Employee" else None
		), patch.object(zoho_books, "_create_time_entry") as create:
			with self.assertRaises(zoho_books.ZohoBooksException):
				zoho_books._sync_timesheet_entries(doc)
			create.assert_not_called()

	def test_queued_job_uses_current_cancelled_status(self):
		doc = frappe._dict(name="test", docstatus=2)
		cache = MagicMock()
		with patch.object(frappe, "cache", return_value=cache), patch.object(
			frappe, "get_doc", return_value=doc
		), patch.object(frappe.db, "set_value") as status, patch.object(
			zoho_books, "_delete_timesheet_entries"
		) as delete, patch.object(zoho_books, "_sync_timesheet_entries") as sync:
			zoho_books.run_timesheet_sync("test")
			delete.assert_called_once_with(doc)
			sync.assert_not_called()
			self.assertEqual(status.call_args.args[2]["custom_zoho_sync_status"], "Cancelled")

	def test_create_intent_is_committed_before_http(self):
		row = frappe._dict(
			name="entry", from_time="2026-01-01 09:00:00", to_time="2026-01-01 10:00:00", is_billable=1
		)
		events = []
		with patch.object(zoho_books, "_get_project_id", return_value="project"), patch.object(
			zoho_books, "_get_task_id", return_value="task"
		), patch.object(
			frappe.db, "set_value", side_effect=lambda *args, **kwargs: events.append(("marker", args[3]))
		), patch.object(
			frappe.db, "commit", side_effect=lambda: events.append(("commit", None))
		), patch.object(
			zoho_books, "_make_api_request", side_effect=lambda *args: events.append(("http", None)) or {}
		):
			with self.assertRaises(zoho_books.ZohoBooksException):
				zoho_books._create_time_entry(row, "user", "token", "org")
		self.assertEqual(events, [("marker", 1), ("commit", None), ("http", None)])

	def test_failed_job_exposes_retryable_status(self):
		doc = frappe._dict(name="test", docstatus=1, time_logs=[frappe._dict(name="mapped")])
		with patch.object(frappe, "cache", return_value=MagicMock()), patch.object(
			frappe, "get_doc", return_value=doc
		), patch.object(frappe.db, "rollback"), patch.object(frappe.db, "set_value") as status, patch.object(
			frappe, "log_error"
		), patch.object(zoho_books, "_get_mapping", return_value="remote"), patch.object(
			zoho_books, "_sync_timesheet_entries", side_effect=zoho_books.ZohoBooksException("offline")
		):
			zoho_books.run_timesheet_sync("test")
			self.assertEqual(status.call_args.args[2]["custom_zoho_sync_status"], "Partial")
			self.assertEqual(status.call_args.args[2]["custom_zoho_sync_error"], "offline")

	def test_reconciliation_records_existing_id_or_confirmed_absence(self):
		for remote_id, absent in (("remote", False), (None, True)):
			doc = MagicMock(docstatus=1, custom_zoho_sync_status="Failed")
			doc.time_logs = [frappe._dict(name="entry", idx=1, custom_zoho_sync_uncertain=1)]
			with patch.object(frappe, "get_doc", side_effect=[MagicMock(), doc]), patch.object(
				frappe, "cache", return_value=MagicMock()
			), patch.object(frappe.db, "set_value") as marker, patch.object(
				frappe.db, "commit"
			), patch.object(zoho_books, "_set_mapping") as mapping:
				zoho_books.reconcile_timesheet_entry("test", 1, remote_id, absent)
				self.assertEqual(marker.call_args.args[3], 0)
				if remote_id:
					mapping.assert_called_once_with("Timesheet Detail", "entry", "remote")
				else:
					mapping.assert_not_called()

	def test_reconciliation_requires_accounting_settings_write_permission(self):
		settings = MagicMock()
		settings.check_permission.side_effect = frappe.PermissionError("denied")
		with patch.object(frappe, "get_doc", return_value=settings), patch.object(
			frappe.db, "set_value"
		) as marker:
			with self.assertRaises(frappe.PermissionError):
				zoho_books.reconcile_timesheet_entry("test", 1, confirmed_absent=True)
			marker.assert_not_called()


class TestTimesheetWeekOfMonth(TestCase):
	def test_week_boundaries_and_month_end(self):
		# September starts on Tuesday: its first week ends on Sunday the 6th.
		for day, week in [
			(1, 1),
			(6, 1),
			(7, 2),
			(13, 2),
			(14, 3),
			(20, 3),
			(21, 4),
			(27, 4),
			(28, 5),
			(30, 5),
		]:
			with self.subTest(day=day):
				self.assertEqual(timesheet.week_of_month(datetime(2026, 9, day, 23, 59)), f"Week {week}")
		self.assertEqual(timesheet.week_of_month("2024-02-29 09:00:00"), "Week 5")
		self.assertEqual(timesheet.week_of_month("2026-10-01 00:00:00"), "Week 1")
		self.assertEqual(timesheet.week_of_month("2026-03-30 00:00:00"), "Week 6")
		self.assertEqual(timesheet.week_of_month("2026-06-01 00:00:00"), "Week 1")

	def test_server_overwrites_supplied_week_and_clears_missing_dates(self):
		rows = [
			frappe._dict(from_time="2026-09-14 09:00:00", custom_week_of_month="Week 5"),
			frappe._dict(from_time=None, custom_week_of_month="Week 3"),
		]
		timesheet._set_week_of_month(frappe._dict(time_logs=rows))
		self.assertEqual([row.custom_week_of_month for row in rows], ["Week 3", ""])


class TestTimesheetWeekOfMonthPatch(FrappeTestCase):
	def test_corrupt_from_time_is_blanked_instead_of_erroring(self):
		from opero.patches.v0_4.add_timesheet_week_of_month import execute

		name = "patch-test-" + frappe.generate_hash(length=12)
		frappe.db.sql(
			"""
			INSERT INTO `tabTimesheet Detail` (name, parent, parentfield, parenttype, from_time)
			VALUES (%s, %s, 'time_logs', 'Timesheet', '2008-00-00 00:00:00')
			""",
			(name, name),
		)
		self.addCleanup(frappe.db.sql, "DELETE FROM `tabTimesheet Detail` WHERE name = %s", (name,))
		execute()
		self.assertEqual(frappe.db.get_value("Timesheet Detail", name, "custom_week_of_month"), "")
