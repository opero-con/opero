from frappe.model.document import Document

from opero import entity


class ProjectBudget(Document):
	def autoname(self):
		self.name = entity.entity_series_name(self, ".{project}./.YYYY./.##")
