"""Add a derived week-of-month label to each timesheet entry."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Timesheet Detail": [
				{
					"fieldname": "custom_week_of_month",
					"label": "Week of Month",
					"fieldtype": "Data",
					"insert_after": "from_time",
					"read_only": 1,
					"in_list_view": 0,
					"columns": 1,
					"description": "Monday-Sunday calendar weeks from this row's From Time. The partial week containing the 1st is Week 1.",
				},
			],
		}
	)

	# Derived metadata only: retain parent status and modification timestamps.
	# The zero-day/zero-month branch guards against corrupt legacy from_time values
	# (e.g. '2008-00-00'): calendar functions like WEEKDAY() error on those under
	# strict SQL modes, so they're detected via string matching before any date
	# arithmetic runs.
	frappe.db.sql(
		"""
		UPDATE `tabTimesheet Detail`
		SET custom_week_of_month = CASE WHEN from_time IS NULL THEN ''
		    WHEN CAST(from_time AS CHAR) REGEXP '-00-|-00 ' THEN ''
		    ELSE CONCAT('Week ', FLOOR((DAY(from_time) - 1 +
		    WEEKDAY(DATE_SUB(DATE(from_time), INTERVAL (DAY(from_time) - 1) DAY))) / 7) + 1) END
		"""
	)
