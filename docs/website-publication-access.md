# Website publication access

Use the Blogger **role profile** and Website Publications
module profile for a System User who prepares and deploys publications. The role
profile uses Frappe's existing **Blogger** role; Opero creates no publisher role.
Role Permission Manager controls document access. The module profile and Site
Content workspace control navigation, not API authorization.

Blogger permits reading, creating, editing, and deploying Publication records.
Publication Type and Publication Topic are read-only lookup data. The profile
also inherits Frappe's standard Blogger permissions on native Blog Post, Blogger,
Blog Category, and Blog Settings documents, even though the module profile hides
the Website module. It is a content-author profile, not an API sandbox limited to
Opero Publication records. Changes to Blogger permissions apply to all Blogger
users, regardless of their role profile.

The Blogger role does not grant deleting or sharing publications, changing Site
Settings, opening Deploy Center, bulk deploying, loading website content, or
accessing employee, finance, project, enterprise, enquiry, or mailing-list records.
Existing Employee and Employee Self Service roles are preserved when renaming
the profile and replacing the obsolete role; their staff permissions remain
effective. Publication editors without Site Settings write access cannot use incidental All
permissions to read enquiries or mailing data. Explicit Role Permission Manager
grants through staff roles remain effective; adding Newsletter Manager or Inbox
User intentionally grants those capabilities.

Each saved publication's Deploy button includes only its own file, media, and
rename pair. Server authorization requires write permission on that Publication,
independent of role names. General deployment and repository loading continue to
require Site Settings write permission. Private attachments are permission-checked
for users without Site Settings write permission.

Assign the two profiles and set the default workspace to Site Content. Remove
broad roles and audit document shares before treating an account as a content
author: Frappe permissions are additive. Do not add Website Manager or System
Manager unless broader access is intended.

The migration renames the legacy publisher role profile to Blogger, preserving
linked user assignments, and transfers legacy publisher role assignments to Blogger,
updates publication-specific Custom DocPerm rows and the Site Content workspace,
and deletes the obsolete role. It retains existing Blogger custom permission
rules when both roles already have a rule at the same permission level and
ownership condition. It does not merge unrelated legacy permission rules into
Blogger. Remaining permission rules for the obsolete role are removed rather
than transferred. New installations never create the role. User-specific profile assignments on the live site
remain an administrator's separate action.
