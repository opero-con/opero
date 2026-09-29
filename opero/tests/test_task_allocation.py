"""Task Allocation submission, derived totals, capacity, the Task grid, and the Task Time Distribution copy."""

from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.events import task as task_events
from opero.opero.doctype.task_allocation import task_allocation
from opero.patches.v0_4 import copy_task_time_distribution_to_task_allocation as copy_patch


class TestTaskAllocation(FrappeTestCase):
	def setUp(self):
		self.previous_user = frappe.session.user
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, self.previous_user)
		self.employee = self._record(
			"Employee", first_name="Allocation test", employee_name="Allocation test"
		)
		self.project = self._record(
			"Project", project_name="Allocation test " + frappe.generate_hash(length=12)
		)
		self.task = self._record(
			"Task",
			subject="Allocation test",
			project=self.project,
			exp_start_date="2026-01-15",
			exp_end_date="2026-03-10",
		)

	def _record(self, doctype, **values):
		doc = frappe.get_doc(
			dict(doctype=doctype, name="alloc-test-" + frappe.generate_hash(length=12), **values)
		)
		doc.db_insert()
		return doc.name

	def _allocate(self, day, hours, submit=True, task=None):
		month = task_allocation.get_month_fields(day)
		doc = frappe.get_doc(
			dict(
				doctype="Task Allocation",
				task=task or self.task,
				employee=self.employee,
				month=month["month"],
				year=month["year"],
				hours=hours,
			)
		).insert()
		if submit:
			doc.submit()
		return doc

	def _submit_timesheet(self, day, hours):
		sheet = self._record("Timesheet", employee=self.employee, parent_project=self.project, docstatus=1)
		self._record(
			"Timesheet Detail",
			parent=sheet,
			parenttype="Timesheet",
			parentfield="time_logs",
			task=self.task,
			from_time=f"{day} 09:00:00",
			hours=hours,
		)

	def _totals(self):
		return (
			frappe.db.get_value("Task", self.task, "custom_total_hours"),
			frappe.db.get_value("Project", self.project, "custom_allocated_hours"),
		)

	def test_month_start_and_project_are_derived(self):
		doc = self._allocate("2026-02-17", 8)
		self.assertEqual((doc.month, doc.year, str(doc.month_start)), ("Feb", "2026", "2026-02-01"))
		self.assertEqual(doc.project, self.project)

	def test_name_is_prefix_creation_month_and_counter_without_entity(self):
		company = frappe.db.get_value("Company", {}, "name")
		frappe.db.set_value("Project", self.project, "company", company)
		self.assertRegex(
			self._allocate("2026-12-01", 1).name, rf"^TAL{frappe.utils.nowdate()[2:4]}\d{{2}}[1-9]\d*$"
		)

	def test_year_must_be_four_digits(self):
		doc = frappe.get_doc(
			dict(
				doctype="Task Allocation",
				task=self.task,
				employee=self.employee,
				month="Feb",
				year="26",
				hours=1,
			)
		)
		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_only_submitted_allocations_count(self):
		draft = self._allocate("2026-01-01", 10, submit=False)
		self.assertEqual(self._totals(), (0, 0))
		draft.submit()
		self._allocate("2026-02-01", 5.5)
		self.assertEqual(self._totals(), (15.5, 15.5))
		draft.cancel()
		self.assertEqual(self._totals(), (5.5, 5.5))

	def test_same_month_allows_several_submitted_allocations(self):
		first = self._allocate("2026-02-01", 2)
		second = self._allocate("2026-02-20", 7)
		self.assertEqual(self._totals(), (9, 9))
		self.assertEqual(
			task_allocation.get_same_task_allocations(
				self.task, self.employee, date(2026, 2, 1), exclude=second.name
			),
			[{"name": first.name, "hours": 2}],
		)

	def test_cancel_cannot_leave_submitted_timesheets_uncovered(self):
		first = self._allocate("2026-01-01", 10)
		self._submit_timesheet("2026-01-12", 6)
		with self.assertRaises(frappe.ValidationError):
			first.cancel()
		self._allocate("2026-01-05", 6)
		first.reload()
		first.cancel()

	def test_grid_sums_submitted_allocations_and_used_hours(self):
		self._allocate("2026-05-01", 4)
		self._allocate("2026-05-09", 1.5)
		self._allocate("2026-05-12", 100, submit=False)
		self._submit_timesheet("2026-01-20", 3)
		grid = task_allocation.get_allocation_grid(self.task)
		self.assertEqual(grid["months"], ["2026-01-01", "2026-02-01", "2026-03-01", "2026-05-01"])
		self.assertEqual(grid["allocated"], [[self.employee, "2026-05-01", 5.5]])
		self.assertEqual(grid["used"], [[self.employee, "2026-01-01", 3.0]])

	def test_allocations_move_with_the_task_project(self):
		self._allocate("2026-01-01", 10)
		other = self._record("Project", project_name="Allocation test " + frappe.generate_hash(length=12))
		task = frappe.get_doc("Task", self.task)
		task._doc_before_save = frappe.get_doc("Task", self.task)
		task.project = other
		task_events._move_allocations_with_task(task)
		self.assertEqual(frappe.db.get_value("Task Allocation", {"task": self.task}, "project"), other)
		self.assertEqual(frappe.db.get_value("Project", other, "custom_allocated_hours"), 10)
		self.assertEqual(frappe.db.get_value("Project", self.project, "custom_allocated_hours"), 0)

	def test_month_must_be_one_of_the_options(self):
		with self.assertRaises(frappe.ValidationError):
			task_allocation.get_month_start("Sept", "2026")

	def test_capacity_counts_every_task_but_the_excluded_record(self):
		mine = self._allocate("2026-02-01", 10)
		other_task = self._record("Task", subject="Allocation test two", project=self.project)
		self._allocate("2026-02-01", 6, task=other_task)
		self._allocate("2026-02-01", 50, submit=False, task=other_task)
		capacity = task_allocation.get_capacity(self.employee, date(2026, 2, 1), exclude=mine.name)
		self.assertEqual(capacity["allocated"], 6)

	def test_over_capacity_warns_on_submit_but_submits(self):
		frappe.clear_messages()
		with patch.object(task_allocation, "get_available_hours", return_value=20):
			doc = self._allocate("2026-02-01", 25, submit=False)
			self.assertEqual(frappe.get_message_log(), [])
			doc.submit()
		self.assertEqual(doc.docstatus, 1)
		self.assertIn("5h over", " ".join(message["message"] for message in frappe.get_message_log()))

	def test_available_hours_follow_holidays_and_attendance(self):
		standard_hours = frappe.db.get_single_value("HR Settings", "standard_working_hours")
		frappe.db.set_single_value("HR Settings", "standard_working_hours", 7)
		self.addCleanup(frappe.db.set_single_value, "HR Settings", "standard_working_hours", standard_hours)
		holidays = self._record(
			"Holiday List", holiday_list_name="Allocation test", from_date="2026-01-01", to_date="2026-12-31"
		)
		weekends = [date(2026, 2, day) for day in (1, 7, 8, 14, 15, 21, 22, 28)]
		for day in [*weekends, date(2026, 2, 10)]:
			self._record(
				"Holiday",
				parent=holidays,
				parenttype="Holiday List",
				parentfield="holidays",
				holiday_date=day,
			)
		frappe.db.set_value(
			"Employee",
			self.employee,
			{"holiday_list": holidays, "status": "Active", "date_of_joining": "2020-01-01"},
		)
		for day, status in (("2026-02-11", "On Leave"), ("2026-02-12", "Half Day")):
			self._record(
				"Attendance", employee=self.employee, attendance_date=day, status=status, docstatus=1
			)
		self.assertEqual(task_allocation.get_available_hours(self.employee, date(2026, 2, 1)), 17.5 * 7)
		self.assertIsNone(task_allocation.get_available_hours(self.employee, date(2027, 2, 1)))


COPY_TASKS = {
	"T1": frappe._dict(
		exp_start_date=date(2025, 1, 14), exp_end_date=date(2025, 6, 30), project_start_date=None
	),
	"T2": frappe._dict(exp_start_date=None, exp_end_date=None, project_start_date=date(2026, 4, 1)),
}


class TestTaskTimeDistributionCopy(FrappeTestCase):
	def _row(self, task, month, hours, deliverables="", employee="E1"):
		return frappe._dict(
			task=task, employee=employee, month=month, hours=hours, deliverables=deliverables, row_name="r"
		)

	def test_monthly_rows_win_and_are_merged(self):
		allocations = copy_patch.build_allocations(
			[
				self._row("T1", "Jan 2025", 3),
				self._row("T1", "January", 2, "kickoff"),
				self._row("T1", "Sept 2025", 1),
				self._row("T1", "Feb 2025", 0),
			],
			[frappe._dict(task="T1", employee="E1", hours=100)],
			COPY_TASKS,
		)
		self.assertEqual(
			{key: entry["hours"] for key, entry in allocations.items()},
			{("T1", "E1", date(2025, 1, 1)): 5, ("T1", "E1", date(2025, 9, 1)): 1},
		)
		self.assertEqual(allocations[("T1", "E1", date(2025, 1, 1))]["deliverables"], ["kickoff"])

	def test_totals_without_months_land_in_the_end_month(self):
		allocations = copy_patch.build_allocations(
			[self._row("T1", "Feb 2025", 0)], [frappe._dict(task="T1", employee="E2", hours=40)], COPY_TASKS
		)
		self.assertEqual(allocations[("T1", "E2", date(2025, 6, 1))]["hours"], 40)

	def test_blank_month_on_undated_task_uses_project_start(self):
		allocations = copy_patch.build_allocations([self._row("T2", None, 21)], [], COPY_TASKS)
		self.assertEqual(list(allocations), [("T2", "E1", date(2026, 4, 1))])

	def test_task_connection_moves_from_task_time_distribution(self):
		frappe.db.delete(
			"DocType Link",
			{"parent": "Task", "link_doctype": ["in", ["Task Allocation", "Task Time Distribution"]]},
		)
		legacy = frappe.get_doc(
			{
				"doctype": "DocType Link",
				"parent": "Task",
				"parenttype": "Customize Form",
				"parentfield": "links",
				"group": "Links",
				"custom": 1,
				"link_doctype": "Task Time Distribution",
				"link_fieldname": "project_task",
			}
		)
		legacy.db_insert()
		copy_patch.link_task_to_allocations()
		self.assertEqual(
			frappe.db.get_value("DocType Link", legacy.name, ["link_doctype", "link_fieldname"]),
			("Task Allocation", "task"),
		)
		copy_patch.link_task_to_allocations()
		self.assertEqual(
			frappe.db.count("DocType Link", {"parent": "Task", "link_doctype": "Task Allocation"}), 1
		)

	def test_unreadable_month_fails(self):
		with self.assertRaises(frappe.ValidationError):
			copy_patch.build_allocations([self._row("T1", "Q3", 5)], [], COPY_TASKS)
