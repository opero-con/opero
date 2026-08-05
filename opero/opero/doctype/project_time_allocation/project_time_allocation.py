"""Project Time Allocation — available hours + share (ported from FC Server Scripts)."""

from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class ProjectTimeAllocation(Document):
	def validate(self):
		self._calculate_available_hours()

	def on_update(self):
		self._share_with_personnel()

	def after_insert(self):
		self._share_with_personnel()

	def _calculate_available_hours(self):
		"""Ported from FC 'Available Hrs' (was wired to non-existent Time Allocation)."""
		working_hours = float(
			frappe.db.get_single_value("HR Settings", "standard_working_hours") or 0
		)
		employee = self.personnel

		for detail in self.time_allocation_detail or []:
			from_date = detail.date_from
			to_date = detail.date_to
			if not (from_date and to_date):
				continue

			from_date = getdate(from_date)
			to_date = getdate(to_date)
			num_days = (to_date - from_date).days + 1

			holidays = frappe.db.count(
				"Holiday",
				filters={"holiday_date": ("between", [from_date, to_date])},
			)
			leave_days = 0
			if employee:
				leave_days = frappe.db.count(
					"Attendance",
					filters={
						"employee": employee,
						"attendance_date": ("between", [from_date, to_date]),
						"status": "On Leave",
					},
				)

			detail.available_hours = (num_days - holidays - leave_days) * working_hours

	def _share_with_personnel(self):
		"""Ported from FC 'Auto Share Records' (was on child Task Time Allocation)."""
		if not self.personnel:
			return
		user_id = frappe.db.get_value("Employee", self.personnel, "user_id")
		if not user_id or user_id.lower() == "administrator":
			return
		if frappe.db.exists(
			"DocShare",
			{
				"share_doctype": "Project Time Allocation",
				"share_name": self.name,
				"user": user_id,
			},
		):
			return
		frappe.share.add(
			doctype="Project Time Allocation",
			name=self.name,
			user=user_id,
			read=1,
		)
