"""Legacy controller needed only while the Employee migration drains this table.

There is deliberately no DocType JSON: model sync must not recreate Team Member.
"""

from frappe.model.document import Document


class TeamMember(Document):
	pass
