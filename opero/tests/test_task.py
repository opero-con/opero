"""Regression coverage for Task Time Distribution allocation growth."""

import frappe
from frappe.tests.utils import FrappeTestCase

from opero.events import task


class TestTaskTimeDistributionGrowth(FrappeTestCase):
	def setUp(self):
		self.previous_user = frappe.session.user
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, self.previous_user)
		self.employee = self._record(
			"Employee", first_name="Task regression", employee_name="Task regression"
		)
		self.project = self._record(
			"Project", project_name="Task regression " + frappe.generate_hash(length=12)
		)
		self.task = self._record("Task", subject="Task regression", project=self.project)
		self.ttd = self._record(
			"Task Time Distribution",
			personnel=self.employee,
			project_task=self.task,
			project=self.project,
			days_allocated=12,
			hours_allocated=100,
		)
		for month, days, hours in (("Jan 2025", 6, 50), ("Feb 2025", 6, 50)):
			self._record(
				"Task Time Distribution Spread",
				parent=self.ttd,
				parenttype="Task Time Distribution",
				parentfield="task_time_distribution_spread",
				month=month,
				days_spread=days,
				time_spread=hours,
			)

	def _record(self, doctype, **values):
		doc = frappe.get_doc(
			dict(doctype=doctype, name="task-test-" + frappe.generate_hash(length=12), **values)
		)
		doc.db_insert()
		return doc.name

	def test_allocation_increase_lands_on_current_month_not_history(self):
		match = frappe._dict(name=self.ttd, days_allocated=12, hours_allocated=100)
		person = {"personnel": self.employee, "days": 16, "hours": 130}

		task._grow_distribution_spread(match, person)

		ttd = frappe.get_doc("Task Time Distribution", self.ttd)
		self.assertEqual(ttd.days_allocated, 16)
		self.assertEqual(ttd.hours_allocated, 130)

		by_month = {row.month: row for row in ttd.task_time_distribution_spread}
		self.assertEqual(by_month["Jan 2025"].days_spread, 6)
		self.assertEqual(by_month["Feb 2025"].days_spread, 6)

		from frappe.utils import now_datetime

		current_month = now_datetime().strftime("%b %Y")
		self.assertEqual(by_month[current_month].days_spread, 4)
		self.assertEqual(by_month[current_month].time_spread, 30)

		self.assertEqual(ttd.total_days_distributed, 16)
		self.assertEqual(ttd.total_hours_distributed, 130)

	def test_allocation_decrease_does_not_touch_spread(self):
		match = frappe._dict(name=self.ttd, days_allocated=12, hours_allocated=100)
		person = {"personnel": self.employee, "days": 10, "hours": 80}

		task._grow_distribution_spread(match, person)

		ttd = frappe.get_doc("Task Time Distribution", self.ttd)
		self.assertEqual(ttd.days_allocated, 10)
		self.assertEqual(ttd.hours_allocated, 80)
		self.assertEqual(len(ttd.task_time_distribution_spread), 2)
