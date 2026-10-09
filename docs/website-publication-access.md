# Website publication access

Use the Website Publication Publisher role profile and Website Publications
module profile for a System User who prepares and deploys publications. The
existing Site Content workspace is shared with website staff. Role Permission
Manager controls access to its documents; the workspace is not a security boundary.
The module profile includes Opero Site and Opero, which is needed to display the
parent sidebar entry. It grants no document permissions.

The role permits reading, creating, editing, and deploying Publication records.
Publication Type and Publication Topic are read-only lookup data. It does not
permit deleting or sharing publications, changing Site Settings, opening Deploy
Center, bulk deploying, loading website content, or accessing employee, finance,
project, enterprise, enquiry, and mailing-list records.

Deployment is available from each saved publication's Deploy button, including
its own media and rename pair. Server authorization checks the role, document
kind, and write permission. General deployment and repository loading remain
restricted to users who can write Site Settings.

Assign the two profiles and set the default workspace to Site Content.
Remove broad roles and audit document shares before treating the account as
website-only: Frappe permissions are additive, and module profiles control Desk
navigation rather than API authorization. Do not add Website Manager or System
Manager to this account. User-specific assignments are not installed by this
migration and must be applied to the intended live site separately.
