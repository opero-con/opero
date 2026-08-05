from frappe.model.document import Document

from opero import entity


class BudgetLine(Document):
	def autoname(self):
		"""`<ABBR>-<code>-<description>`.

		The code alone is only unique inside one entity — both entities can run a
		budget line "1.1 Personnel" — so the entity has to be part of the key.
		"""
		abbr = entity.entity_abbr(self)
		if not (abbr and self.code):
			return
		self.name = "-".join(part for part in (abbr, self.code, self.description) if part)
