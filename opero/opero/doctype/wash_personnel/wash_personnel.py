from frappe.model.document import Document


class WASHPersonnel(Document):
	def validate(self):
		if self.first_name or self.middle_name or self.last_name:
			middle_initial = f"{self.middle_name[0]}." if self.middle_name else ""
			self.full_name = f"{self.first_name or ''} {middle_initial} {self.last_name or ''}".strip()
