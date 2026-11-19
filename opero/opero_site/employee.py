"""Website team behavior layered onto Frappe's Employee DocType."""

import frappe
from erpnext.setup.doctype.employee.employee import Employee as FrappeEmployee
from frappe import _
from frappe.utils import cint, cstr

from opero.opero_site.publish_status import apply_publish_status, is_on_site
from opero.opero_site.utils import optional_url, slugify

PERSONNEL_TYPE_SERIES = {"Staff": "OSL_EMP_.###", "Consultant": "OSL_CON_.###"}


class Employee(FrappeEmployee):
	"""Keep Employee's HR behavior and add the public team profile contract."""

	def before_naming(self):
		series = PERSONNEL_TYPE_SERIES.get(self.get("custom_personnel_type"))
		if series and cstr(self.naming_series) in ("", *PERSONNEL_TYPE_SERIES.values()):
			self.naming_series = series
		self.set_employee_name()
		self.set_slug()

	def validate(self):
		FrappeEmployee.validate(self)
		self.set_slug()
		self.role = cstr(self.role).strip()
		self.linkedin = optional_url(self.linkedin, "LinkedIn URL")
		apply_publish_status(self)
		self.sort_order = cint(self.sort_order)

	def set_slug(self):
		"""Website slug from the employee name; only employees with a website file have one."""
		if not (cint(self.show_on_website) or self.slug):
			return
		self.slug = slugify(self.employee_name)
		if not self.slug:
			frappe.throw(_("Slug must contain at least one letter or number."))
		other = frappe.db.get_value("Employee", {"slug": self.slug, "name": ["!=", self.name or ""]})
		if other:
			frappe.throw(_("{0} is already on the website as {1}.").format(self.employee_name, other))

	def to_site_frontmatter(self):
		payload = {
			"name": self.employee_name,
			"role": cstr(self.role).strip(),
			"image": cstr(self.portrait if cint(self.use_alternative_image) else self.image),
			"imageAlt": f"Portrait of {self.employee_name}",
			"order": cint(self.sort_order),
			"active": is_on_site(self),
		}
		if self.linkedin:
			payload["linkedin"] = self.linkedin
		return payload
