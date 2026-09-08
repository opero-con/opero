"""Drop Email Group Member.custom_confirmation_status after confirmation removal.

Sites that already ran drop_mailing_confirmation kept a Confirmed-only
Subscription Status field. Membership eligibility is Unsubscribed only.
"""

from opero.patches.v0_4.drop_mailing_confirmation import _drop_confirmation_status_field


def execute():
	_drop_confirmation_status_field()
