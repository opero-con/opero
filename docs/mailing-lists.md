# Mailing Lists

Opero uses Frappe's Email Group, Email Group Member, and Newsletter records.
Their displayed names are **Mailing List** and **Emailing List Member**;
the internal DocType names and existing routes remain unchanged.

## Add a member using a Contact

Open an Emailing List Member, choose its Mailing List, and select **Contact**.
The Contact link is available in both Quick Entry and the full form. It searches
the Contacts you can access and fills the selected Contact's primary email.
**Mobile No** is shown only when Contact is set (fetched from the Contact) and
is available in list view and export. Clear Contact to enter a standalone email
address instead.

A Contact needs a primary email to create an Emailing List Member. Contacts
without an email can still have lists assigned from the Contact form; those
memberships show **No email** until a primary address is added.

Saving a member does not send email. New members are eligible for newsletters
immediately. An address can appear only once in each Mailing List.

## Manage membership

The Contact form has a **Mailing Lists** Table MultiSelect and a read-only
status table below it. Members added or removed from either side synchronize.
Contacts sharing a primary email share memberships and unsubscribe status.
Changing a primary email carries memberships to the new address; any
unsubscribe is preserved. Other Contacts still using the old address keep
their subscriptions.

The Contact list's **Mailing List filters** support Any or All selected lists
and membership status. **Export with Mailing List status** exports matching
Contacts, with one row per relevant membership. **Manage Mailing Lists** under
Actions adds or removes memberships for selected Contacts. Standard Contact
data imports can include the Mailing Lists child records.

## Delivery and unsubscribe

Use the existing **Action → New Newsletter** on a Mailing List. Newsletter
recipients are members who are not unsubscribed; shared addresses receive one
copy. Every newsletter includes Frappe's unsubscribe link in the footer, which
supports selecting individual lists or all current lists. Newsletter Managers
can clear **Unsubscribed** to reactivate a member, with changes tracked. List
renaming and deletion retain native behavior.

Contact editors manage memberships. Newsletter Managers create lists and send
newsletters. Selecting a Contact does not grant additional permission to view
or edit it.
