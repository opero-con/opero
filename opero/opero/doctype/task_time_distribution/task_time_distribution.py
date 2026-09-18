from frappe.model.document import Document

from opero import entity


class TaskTimeDistribution(Document):
	def autoname(self):
		self.name = entity.entity_series_name(self, "TTD-.YY..MM.-.####")

	def validate(self):
		self.total_days_distributed = sum(
			float(row.days_spread or 0) for row in self.task_time_distribution_spread
		)
		self.total_hours_distributed = sum(
			float(row.time_spread or 0) for row in self.task_time_distribution_spread
		)
