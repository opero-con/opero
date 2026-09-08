"""Exercise real Frappe documents; intercept mail and roll back all test data."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import cint

from opero.mailing import confirmation as confirm_api
from opero.mailing import membership as m
from opero.mailing.filters import export_rows, matching_names
from opero.mailing.overrides import add_subscribers


class TestMailingLists(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.savepoint("mailing_test")
		self.mail = patch("frappe.sendmail").start()
		self.addCleanup(patch.stopall)
		self.prefix = "_Mailing Test " + frappe.generate_hash(length=8)
		self.a = frappe.get_doc({"doctype": "Email Group", "title": self.prefix + " A"}).insert()
		self.b = frappe.get_doc({"doctype": "Email Group", "title": self.prefix + " B"}).insert()
		self.email = frappe.generate_hash(length=10) + "@example.test"

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="mailing_test")

	def contact(self, email=None, groups=()):
		return frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": self.prefix + frappe.generate_hash(length=5),
				"email_ids": [{"email_id": email, "is_primary": 1}] if email else [],
				m.FIELD: [{"mailing_list": g} for g in groups],
			}
		).insert()

	def member(self, group=None, email=None):
		return frappe.get_doc(m.MEMBER, {"email_group": group or self.a.name, "email": email or self.email})

	def test_contact_add_is_confirmed_and_never_sends(self):
		c = self.contact(self.email, [self.a.name, self.b.name])
		self.assertEqual(m.status(self.member()), "Confirmed")
		self.assertEqual({r.subscription_status for r in c.reload().get(m.FIELD)}, {"Confirmed"})
		self.mail.assert_not_called()
		newsletter = frappe.new_doc("Newsletter")
		newsletter.append("email_group", {"email_group": self.a.name})
		self.assertIn(self.email, newsletter.get_recipients())

	def test_member_can_be_added_by_selecting_contact(self):
		contact = self.contact(self.email)
		member = frappe.get_doc(
			{
				"doctype": m.MEMBER,
				"email_group": self.a.name,
				"custom_contact": contact.name,
			}
		).insert()
		self.assertEqual(member.email, self.email)
		self.assertEqual(member.custom_contact, contact.name)
		self.assertEqual(m.status(member), "Confirmed")
		self.assertEqual(contact.reload().get(m.FIELD)[0].mailing_list, self.a.name)
		self.mail.assert_not_called()

	def test_selected_contact_is_authoritative_for_email(self):
		contact = self.contact(self.email)
		member = frappe.get_doc(
			{
				"doctype": m.MEMBER,
				"email_group": self.a.name,
				"custom_contact": contact.name,
				"email": "different@example.test",
			}
		).insert()
		self.assertEqual(member.email, self.email)

	def test_selected_contact_needs_a_primary_email(self):
		contact = self.contact()
		with self.assertRaisesRegex(frappe.ValidationError, "primary email"):
			frappe.get_doc(
				{
					"doctype": m.MEMBER,
					"email_group": self.a.name,
					"custom_contact": contact.name,
				}
			).insert()

	def test_selected_contact_link_follows_primary_email_change(self):
		contact = self.contact(self.email)
		frappe.get_doc(
			{
				"doctype": m.MEMBER,
				"email_group": self.a.name,
				"custom_contact": contact.name,
			}
		).insert()
		contact.reload()
		contact.email_ids[0].email_id = "new-" + self.email
		contact.save()
		member = self.member(email=contact.email_id)
		self.assertEqual(member.custom_contact, contact.name)
		self.assertEqual(m.status(member), "Confirmed")

	def test_contact_email_lookup_requires_contact_read_permission(self):
		contact = self.contact(self.email)
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			m.contact_primary_email(contact.name)

	def test_manager_can_clear_unsubscribed_and_history_is_retained(self):
		self.contact(self.email, [self.a.name])
		doc = self.member()
		doc.unsubscribed = 1
		doc.save()
		doc.unsubscribed = 0
		doc.save()
		self.assertEqual(m.status(doc), "Confirmed")
		self.assertTrue(
			frappe.db.exists("Mailing Membership Event", {"member": doc.name, "action": "Status changed"})
		)

	def test_shared_primary_email_add_remove_and_status(self):
		one = self.contact(self.email, [self.a.name])
		two = self.contact(self.email)
		self.assertEqual([r.mailing_list for r in two.reload().get(m.FIELD)], [self.a.name])
		two.append(m.FIELD, {"mailing_list": self.b.name})
		two.save()
		self.assertEqual(len(one.reload().get(m.FIELD)), 2)
		one.set(m.FIELD, [])
		one.save()
		self.assertEqual(two.reload().get(m.FIELD), [])
		self.assertFalse(frappe.db.exists(m.MEMBER, {"email": self.email}))

	def test_standalone_add_links_matching_contact_without_sending(self):
		c = self.contact(self.email)
		add_subscribers(self.a.name, self.email)
		self.assertEqual(c.reload().get(m.FIELD)[0].mailing_list, self.a.name)
		self.mail.assert_not_called()

	def test_primary_email_moves_and_preserves_unsubscribe(self):
		c = self.contact(self.email, [self.a.name, self.b.name])
		doc = self.member(self.b.name)
		doc.unsubscribed = 1
		doc.save()
		c.reload()
		c.email_ids[0].email_id = "new-" + self.email
		c.save()
		self.assertEqual(m.status(self.member(email=c.email_id)), "Confirmed")
		self.assertEqual(m.status(self.member(self.b.name, c.email_id)), "Unsubscribed")
		self.assertFalse(frappe.db.exists(m.MEMBER, {"email": self.email}))

	def test_shared_old_address_is_retained_on_email_change(self):
		c = self.contact(self.email, [self.a.name])
		other = self.contact(self.email)
		c.reload()
		c.email_ids[0].email_id = "new-" + self.email
		c.save()
		self.assertEqual(len(other.reload().get(m.FIELD)), 1)
		self.assertTrue(frappe.db.exists(m.MEMBER, {"email": self.email}))

	def test_without_email_then_add_primary(self):
		c = self.contact(groups=[self.a.name])
		self.assertEqual(c.get(m.FIELD)[0].subscription_status, "No email")
		self.assertFalse(frappe.db.exists(m.MEMBER, {"email_group": self.a.name}))
		c.append("email_ids", {"email_id": self.email, "is_primary": 1})
		c.save()
		self.assertEqual(m.status(self.member()), "Confirmed")
		self.mail.assert_not_called()

	def test_removal_preserves_history_and_rejoin_is_confirmed(self):
		c = self.contact(self.email, [self.a.name])
		member = self.member()
		c.reload().set(m.FIELD, [])
		c.save()
		self.assertTrue(
			frappe.db.exists("Mailing Membership Event", {"member": member.name, "action": "Removed"})
		)
		c.reload().append(m.FIELD, {"mailing_list": self.a.name})
		c.save()
		self.assertEqual(m.status(self.member()), "Confirmed")
		self.assertTrue(
			frappe.db.exists("Mailing Membership Event", {"member": self.member().name, "action": "Added"})
		)

	def test_any_all_status_filter_and_export(self):
		one = self.contact(self.email, [self.a.name, self.b.name])
		two = self.contact("second-" + self.email, [self.a.name])
		base = {"mailing_lists": [self.a.name, self.b.name]}
		self.assertEqual(set(matching_names(base)), {one.name, two.name})
		self.assertEqual(matching_names({**base, "match": "All"}), [one.name])
		self.member(self.b.name).db_set("unsubscribed", 1)
		m.sync_email(self.email)
		self.assertEqual(matching_names({**base, "match": "All", "status": "Confirmed"}), [])
		self.assertEqual(matching_names({**base, "status": "Confirmed"}), [one.name, two.name])
		rows = export_rows(mailing_filter={**base, "match": "All"})
		self.assertEqual(len(rows), 3)
		self.assertEqual({r[-1] for r in rows[1:]}, {"Confirmed", "Unsubscribed"})

	def test_existing_members_stay_eligible(self):
		with m.internal():
			frappe.get_doc(
				{
					"doctype": m.MEMBER,
					"email_group": self.a.name,
					"email": self.email,
				}
			).insert()
		newsletter = frappe.new_doc("Newsletter")
		newsletter.append("email_group", {"email_group": self.a.name})
		newsletter.append("email_group", {"email_group": self.b.name})
		self.assertEqual(newsletter.get_recipients(), [self.email])
		self.contact(self.email)
		self.assertEqual(newsletter.get_recipients(), [self.email])

	def test_guests_cannot_manage(self):
		c = self.contact(self.email, [self.a.name])
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			m.bulk_membership([c.name], [self.b.name])
		with self.assertRaises(frappe.PermissionError):
			export_rows()

	def test_new_members_are_eligible(self):
		doc = frappe.get_doc(
			{
				"doctype": m.MEMBER,
				"email_group": self.a.name,
				"email": self.email,
			}
		).insert()
		self.assertEqual(m.status(doc), "Confirmed")
		self.assertFalse(cint(doc.unsubscribed))

	def test_contact_editor_can_select_and_assign_but_cannot_create_lists(self):
		from frappe.client import validate_link

		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "editor-" + self.email,
				"first_name": "Mailing Editor",
				"send_welcome_email": 0,
				"roles": [{"role": "Sales User"}],
			}
		).insert()
		frappe.set_user(user.name)
		self.assertEqual(validate_link("Email Group", self.a.name).name, self.a.name)
		self.contact(self.email, [self.a.name])
		self.assertEqual(m.status(self.member()), "Confirmed")
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc({"doctype": "Email Group", "title": self.prefix + " Forbidden"}).insert()

	def test_export_and_filtered_list_respect_contact_permissions(self):
		from opero.mailing.filters import get, get_count

		self.contact(self.email, [self.a.name])
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "reader-" + self.email,
				"first_name": "Mailing Reader",
				"send_welcome_email": 0,
				"roles": [{"role": "Newsletter Manager"}],
			}
		).insert()
		frappe.set_user(user.name)
		old_form = frappe.local.form_dict
		try:
			frappe.local.form_dict = frappe._dict(
				doctype="Contact", fields=["name"], opero_mailing_filter={"mailing_lists": [self.a.name]}
			)
			self.assertEqual(get(), [])
			self.assertEqual(get_count(), 0)
			with self.assertRaises(frappe.PermissionError):
				export_rows(mailing_filter={"mailing_lists": [self.a.name]})
		finally:
			frappe.local.form_dict = old_form

	def test_deleting_and_renaming_lists_keep_native_behavior(self):
		c = self.contact(self.email, [self.a.name])
		frappe.rename_doc("Email Group", self.a.name, self.a.name + " Renamed")
		self.assertEqual(c.reload().get(m.FIELD)[0].mailing_list, self.a.name + " Renamed")
		frappe.delete_doc("Email Group", self.a.name + " Renamed")
		self.assertEqual(c.reload().get(m.FIELD), [])

	def test_merging_lists_keeps_unique_and_overlapping_members(self):
		shared = self.email
		only_a = frappe.generate_hash(length=10) + "@example.test"
		only_b = frappe.generate_hash(length=10) + "@example.test"
		both = self.contact(shared, [self.a.name, self.b.name])
		self.contact(only_a, [self.a.name])
		self.contact(only_b, [self.b.name])
		frappe.rename_doc("Email Group", self.a.name, self.b.name, merge=True)
		self.assertFalse(frappe.db.exists("Email Group", self.a.name))
		for email in (shared, only_a, only_b):
			self.assertTrue(
				frappe.db.exists(m.MEMBER, {"email_group": self.b.name, "email": email}), email
			)
		self.assertEqual(m.status(self.member(self.b.name, shared)), "Confirmed")
		self.assertEqual([r.mailing_list for r in both.reload().get(m.FIELD)], [self.b.name])
		self.assertEqual(
			frappe.db.get_value("Email Group", self.b.name, "total_subscribers"),
			3,
		)

	def test_merge_preserves_unsubscribe_from_source_list(self):
		self.contact(self.email, [self.a.name, self.b.name])
		source = self.member(self.a.name)
		source.unsubscribed = 1
		source.save()
		frappe.rename_doc("Email Group", self.a.name, self.b.name, merge=True)
		self.assertEqual(self.member(self.b.name).unsubscribed, 1)

	def test_native_import_saves_confirmed_and_sends_no_welcome(self):
		c = self.contact(self.email)
		# Limit the source query to synthetic Contacts; real Contacts must never be imported by tests.
		native = frappe.get_list

		def source(doctype, *args, **kwargs):
			if doctype == "Contact":
				kwargs["filters"] = {"name": c.name}
			return native(doctype, *args, **kwargs)

		with patch("frappe.get_list", side_effect=source):
			self.a.import_from("Contact")
		self.assertEqual(m.status(self.member()), "Confirmed")
		self.mail.assert_not_called()

	def test_public_signup_reactivates_unsubscribed(self):
		self.contact(self.email, [self.a.name])
		member = self.member()
		member.unsubscribed = 1
		member.save()
		frappe.set_user("Guest")
		# Exercise the service without the HTTP-only rate limiter wrapper.
		confirm_api.subscribe.__wrapped__(self.email, self.a.name)
		self.assertFalse(self.member().unsubscribed)
		self.assertEqual(m.status(self.member()), "Confirmed")
		self.mail.assert_not_called()
