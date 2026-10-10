# Publication publishing uses standard roles and document permissions

- **Status:** Accepted

Blogger is the role profile name, composed of the existing
Frappe Blogger role. Preserve existing Employee and Employee Self Service
assignments in the profile. Do not create an Opero-specific role for this workflow.
Use Role Permission Manager for document permissions and a module profile for
navigation. Blogger is a content-author role and retains its native Frappe blog
permissions; a role profile cannot subtract these additive grants. Website Manager
is too broad for authors because it grants website configuration access.

Deploying one Publication requires write permission on that document. Bulk deploy
and repository loading require Site Settings write permission. Application code
must not require the publisher role's name. Publication editors without settings
access remain excluded from incidental All permissions on enquiries and mailing
data, while explicit grants through staff roles remain effective.

Replace legacy publisher assignments and only publication-specific permission
rules, then delete the legacy role. Preserve existing Blogger custom permission
rules. Do not merge unrelated permissions from the legacy role into Blogger or
change Blogger's native permissions globally.
