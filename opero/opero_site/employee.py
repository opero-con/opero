"""Website team behavior layered onto Frappe's Employee DocType."""

import frappe
from frappe import _
from frappe.utils import cint, cstr

from erpnext.setup.doctype.employee.employee import Employee as FrappeEmployee

from opero.opero_site.publish_status import apply_publish_status, is_on_site
from opero.opero_site.utils import optional_url, slugify


class Employee(FrappeEmployee):
	"""Keep Employee's HR behavior and add the public team profile contract."""

	def before_naming(self):
		self.set_employee_name()
		self.slug = slugify(self.employee_name)
		if not self.slug:
			frappe.throw(_("Slug must contain at least one letter or number."))

	def validate(self):
		FrappeEmployee.validate(self)
		self.slug = slugify(self.employee_name)
		if not self.slug:
			frappe.throw(_("Slug must contain at least one letter or number."))
		self.role = cstr(self.role).strip()
		self.linkedin = optional_url(self.linkedin, "LinkedIn URL")
		apply_publish_status(self)
		self.sort_order = cint(self.sort_order)

	def to_site_frontmatter(self):
		payload = {
			"name": self.employee_name,
			"role": cstr(self.role).strip(),
			"image": cstr(self.image if cint(self.use_employee_image) else self.portrait),
			"imageAlt": f"Portrait of {self.employee_name}",
			"order": cint(self.sort_order),
			"active": is_on_site(self),
		}
		if self.linkedin:
			payload["linkedin"] = self.linkedin
		return payload
