# 0016: Target Frappe v16 and the standalone Newsletter app

Status: accepted for the v16 compatibility branch; deployment pending validation.

Opero's v15 mailing controller imports and workspace endpoint do not exist on
Frappe v16. This branch targets v16 only, with Python 3.14 and an explicit
Newsletter app prerequisite. Opero’s existing handling of optional HRMS metadata
remains in place; the target site already has ERPNext and HRMS. Existing v15 deployments
must stay on their v15 source until the coordinated upgrade.

Use Newsletter's controller and default mailing group, and override both its
new signup endpoints and the historic Frappe endpoints so existing public links
retain Opero's immediate signup and unsubscribe behavior.

Frappe v16 builds multiple navigation surfaces from `desktop.get_workspaces`.
A before-request wrapper filters hidden public workspaces before those surfaces
are built. It retains the native provider and its request cache, copies the
returned mapping, and evaluates roles for each call. The existing boot hook
also filters v16's native `workspaces.pages` payload. System Managers retain
native access; Workspace Manager alone does not reveal hidden public pages.
This remains a navigation policy, not a replacement for document permissions.

Deploy with a target bench containing Newsletter before Opero is migrated.
Do not widen the v15 compatibility range or silently disable mailing when the
new prerequisite is absent. Revisit the wrapper if Frappe exposes a dedicated
workspace visibility hook.
