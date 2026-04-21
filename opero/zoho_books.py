"""Zoho Books integration for Frappe/ERPNext timesheets."""

from __future__ import annotations

import frappe
import requests
from datetime import datetime, timedelta
from frappe.utils import cint, get_datetime, get_url
from typing import Optional, Dict, Any


class ZohoBooksException(Exception):
    """Custom exception for Zoho Books integration errors."""
    pass


ZOHO_OAUTH_CALLBACK_PATH = "/api/method/opero.zoho_books.oauth_callback"


def sync_timesheet_to_zoho(doc, method: str = "submit"):
    """
    Main hook to sync Timesheet to Zoho Books.
    Called on: on_submit, on_amend, on_cancel
    """
    if method == "on_cancel":
        _delete_timesheet_entries(doc)
    elif method == "on_amend":
        _sync_timesheet_entries(doc, is_update=True)
    else:
        _sync_timesheet_entries(doc, is_update=False)


def _sync_timesheet_entries(doc, is_update: bool = False):
    """Sync individual time log entries to Zoho Books."""
    try:
        settings = _get_settings()
        if not settings or not settings.enabled:
            frappe.logger().info("Zoho Books integration not enabled, skipping sync")
            return

        _validate_settings(settings)

        # Get or refresh access token
        access_token = _get_or_refresh_token(settings)
        org_id = settings.organization_id

        # Get employee's Zoho user ID
        zoho_user_id = _get_employee_zoho_user_id(doc.employee)
        if not zoho_user_id:
            frappe.msgprint(
                f"Zoho Books: No personnel mapping found for <b>{doc.employee}</b>. "
                "Add a row in Zoho Books Settings → Personnel Mapping.",
                indicator="orange",
                alert=True,
            )
            return

        # Process each time log
        ts_note = frappe.utils.strip_html(doc.note or "") if getattr(doc, "note", None) else ""
        errors = []
        for time_log in doc.time_logs:
            try:
                notes = getattr(time_log, "description", None) or ts_note
                if is_update and getattr(time_log, "zoho_entry_id", None):
                    _update_time_entry(time_log, zoho_user_id, access_token, org_id, notes)
                else:
                    _create_time_entry(time_log, zoho_user_id, access_token, org_id, notes)
            except ZohoBooksException as e:
                frappe.logger().error(f"Failed to sync time log: {e}")
                errors.append(str(e))

        if errors:
            frappe.msgprint(
                "Zoho Books sync failed for some entries:<br>" + "<br>".join(errors),
                indicator="red",
            )
        else:
            frappe.msgprint("Zoho Books: timesheet synced successfully.", indicator="green", alert=True)

    except ZohoBooksException as e:
        frappe.msgprint(f"Zoho Books sync failed: {e}", indicator="red")


def _delete_timesheet_entries(doc):
    """Delete time log entries from Zoho Books."""
    try:
        settings = _get_settings()
        if not settings or not settings.enabled:
            return

        _validate_settings(settings)
        access_token = _get_or_refresh_token(settings)
        org_id = settings.organization_id

        for time_log in doc.time_logs:
            entry_id = getattr(time_log, "zoho_entry_id", None)
            if entry_id:
                try:
                    _delete_time_entry(entry_id, access_token, org_id)
                except ZohoBooksException as e:
                    frappe.logger().error(f"Failed to delete time entry: {e}")

    except ZohoBooksException as e:
        frappe.logger().error(f"Failed to delete timesheet entries: {e}")


@frappe.whitelist(allow_guest=True)
def oauth_callback():
    """Handle Zoho OAuth redirect and exchange authorization code for tokens."""
    code = frappe.request.args.get("code")
    error = frappe.request.args.get("error")

    if error:
        frappe.respond_as_web_page("Zoho Auth Failed", f"<p>Zoho returned error: {error}</p>", http_status_code=400)
        return

    if not code:
        frappe.respond_as_web_page("Zoho Auth Failed", "<p>No authorization code received.</p>", http_status_code=400)
        return

    settings = frappe.get_doc("Zoho Books Settings")
    redirect_uri = _get_redirect_uri()

    try:
        response = requests.post(
            settings.token_uri,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.client_id,
                "client_secret": settings.get_password("client_secret"),
                "redirect_uri": redirect_uri,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            frappe.respond_as_web_page("Zoho Auth Failed", f"<p>Token error: {data['error']}</p>", http_status_code=400)
            return

        new_expiry = datetime.now() + timedelta(seconds=data.get("expires_in", 3600))
        _save_tokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            token_expiry=new_expiry.isoformat(),
        )

        frappe.respond_as_web_page(
            "Zoho Connected",
            "<p>✅ Zoho Books connected successfully. You can close this tab.</p>",
        )

    except requests.RequestException as e:
        frappe.respond_as_web_page("Zoho Auth Failed", f"<p>Request failed: {e}</p>", http_status_code=500)


@frappe.whitelist()
def get_zoho_users():
    """Fetch all users from Zoho Books Projects."""
    settings = _get_settings()
    _validate_settings(settings)
    access_token = _get_or_refresh_token(settings)
    response = _make_api_request("GET", "users", access_token, settings.organization_id)
    return response.get("users", [])


@frappe.whitelist()
def get_zoho_projects():
    """Fetch all projects from Zoho Books."""
    settings = _get_settings()
    _validate_settings(settings)
    access_token = _get_or_refresh_token(settings)
    response = _make_api_request("GET", "projects", access_token, settings.organization_id)
    return response.get("projects", [])


@frappe.whitelist()
def save_project_mappings(mappings):
    """Save project mappings and write zoho_project_id to each ERPNext Project."""
    import json
    if isinstance(mappings, str):
        mappings = json.loads(mappings)

    settings = frappe.get_doc("Zoho Books Settings")
    settings.project_mapping = []
    for m in mappings:
        settings.append("project_mapping", {
            "erpnext_project": m["erpnext_project"],
            "zoho_project_id": m["zoho_project_id"],
            "zoho_project_name": m["zoho_project_name"],
        })
        frappe.db.set_value("Project", m["erpnext_project"], "zoho_project_id", m["zoho_project_id"])
    settings.save()
    return {"status": "ok"}


@frappe.whitelist()
def get_authorization_url():
    """Build and return the Zoho OAuth authorization URL."""
    settings = frappe.get_doc("Zoho Books Settings")
    import urllib.parse
    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": settings.client_id,
        "scope": settings.scope or "ZohoBooks.timetracking.ALL ZohoBooks.projects.ALL",
        "redirect_uri": _get_redirect_uri(),
        "access_type": "offline",
        "prompt": "consent",
    })
    return f"{settings.authorization_uri}?{params}"


def _get_redirect_uri() -> str:
    """Resolve the OAuth callback for the current site/request."""
    return get_url(ZOHO_OAUTH_CALLBACK_PATH)


def _save_tokens(access_token=None, refresh_token=None, token_expiry=None):
    """Write OAuth tokens directly via Frappe's password store + singles table."""
    from frappe.utils.password import set_encrypted_password
    if access_token:
        set_encrypted_password("Zoho Books Settings", "Zoho Books Settings", access_token, "access_token")
    if refresh_token:
        set_encrypted_password("Zoho Books Settings", "Zoho Books Settings", refresh_token, "refresh_token")
    if token_expiry:
        frappe.db.set_value("Zoho Books Settings", "Zoho Books Settings", "token_expiry", token_expiry)
    frappe.db.commit()


def _get_token(fieldname: str) -> str:
    """Read an OAuth token directly from Frappe's password store."""
    from frappe.utils.password import get_decrypted_password
    try:
        return get_decrypted_password("Zoho Books Settings", "Zoho Books Settings", fieldname, raise_exception=False)
    except Exception:
        return None


def _get_settings() -> Optional[Dict[str, Any]]:
    """Get Zoho Books Settings singleton document."""
    try:
        return frappe.get_doc("Zoho Books Settings")
    except frappe.DoesNotExistError:
        return None


def _validate_settings(settings: Dict[str, Any]):
    """Validate that all required settings are present."""
    if not settings.client_id:
        raise ZohoBooksException("Zoho Books Client ID not configured")
    if not settings.client_secret:
        raise ZohoBooksException("Zoho Books Client Secret not configured")
    if not settings.organization_id:
        raise ZohoBooksException("Zoho Books Organization ID not configured")


def _get_or_refresh_token(settings: Dict[str, Any]) -> str:
    """Get access token, refresh if expired."""
    if _is_token_expired(settings.token_expiry):
        refresh_token = _get_token("refresh_token")
        if not refresh_token:
            raise ZohoBooksException("No refresh token available. Please reconfigure Zoho Books authentication.")
        _refresh_access_token(settings)
        settings.reload()

    return _get_token("access_token")


def _is_token_expired(token_expiry: str) -> bool:
    """Check if token has expired."""
    if not token_expiry:
        return True

    expiry_time = get_datetime(token_expiry)
    # Consider token expired 5 minutes before actual expiry
    return datetime.now() >= (expiry_time - timedelta(minutes=5))


def _refresh_access_token(settings: Dict[str, Any]):
    """Refresh OAuth access token using refresh token."""
    try:
        response = requests.post(
            settings.token_uri,
            data={
                "grant_type": "refresh_token",
                "refresh_token": _get_token("refresh_token"),
                "client_id": settings.client_id,
                "client_secret": settings.get_password("client_secret"),
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        if "error" in data or "access_token" not in data:
            raise ZohoBooksException(
                f"Token refresh failed: {data.get('error', data)}. "
                "Please reconnect via Zoho Books Settings → Connect to Zoho."
            )

        new_expiry = datetime.now() + timedelta(seconds=data.get("expires_in", 3600))
        _save_tokens(access_token=data["access_token"], token_expiry=new_expiry.isoformat())
        settings.reload()

    except requests.RequestException as e:
        raise ZohoBooksException(f"Failed to refresh access token: {e}")


def _make_api_request(
    method: str,
    endpoint: str,
    access_token: str,
    org_id: str,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Make a request to Zoho Books API."""
    url = f"https://www.zohoapis.com/books/v3/{endpoint}"
    params = {"organization_id": org_id}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    try:
        if method.upper() == "POST":
            response = requests.post(url, params=params, json=data, headers=headers, timeout=10)
        elif method.upper() == "PUT":
            response = requests.put(url, params=params, json=data, headers=headers, timeout=10)
        elif method.upper() == "DELETE":
            response = requests.delete(url, params=params, headers=headers, timeout=10)
        else:
            response = requests.get(url, params=params, headers=headers, timeout=10)

        if not response.ok:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise ZohoBooksException(f"Zoho Books API error {response.status_code}: {body}")
        return response.json()

    except ZohoBooksException:
        raise
    except requests.RequestException as e:
        raise ZohoBooksException(f"Zoho Books API request failed: {e}")


def _get_employee_zoho_user_id(employee: str) -> Optional[str]:
    """Look up Zoho user ID for a personnel from the mapping table."""
    settings = _get_settings()
    if not settings or not settings.personnel_mapping:
        return None

    for mapping in settings.personnel_mapping:
        if mapping.personnel_id == employee:
            return mapping.zoho_user_id

    return None


def _get_project_id(time_log) -> str:
    """Get Zoho project ID from time log or fallback."""
    settings = _get_settings()

    # Use zoho_project_id custom field if set on the ERPNext project
    if time_log.project:
        zoho_id = frappe.db.get_value("Project", time_log.project, "zoho_project_id")
        if zoho_id:
            return zoho_id

    # Fall back to configured fallback project
    if settings and settings.fallback_project_id:
        return settings.fallback_project_id

    raise ZohoBooksException("No Zoho project ID found. Set a Fallback Project ID in Zoho Books Settings.")


_zoho_task_cache: Dict[str, Dict[str, str]] = {}


def _get_task_id(time_log, project_id: str, access_token: str, org_id: str) -> Optional[str]:
    """Match ERPNext task name to Zoho task ID by name, fallback to settings."""
    # 1. Already stored on the time log row
    if getattr(time_log, "zoho_task_id", None):
        return time_log.zoho_task_id

    # 2. Try to match by name against Zoho tasks for this project
    erpnext_task = getattr(time_log, "task", None)
    if erpnext_task and project_id:
        task_name = frappe.db.get_value("Task", erpnext_task, "subject") or erpnext_task
        zoho_task_id = _match_zoho_task_by_name(project_id, task_name, access_token, org_id)
        if zoho_task_id:
            return zoho_task_id

    # 3. Fall back to configured fallback task
    settings = _get_settings()
    if settings and settings.fallback_task_id:
        return settings.fallback_task_id

    return None


def _match_zoho_task_by_name(project_id: str, task_name: str, access_token: str, org_id: str) -> Optional[str]:
    """Fetch tasks for a Zoho project and return the ID whose name matches task_name."""
    if project_id not in _zoho_task_cache:
        try:
            response = _make_api_request(
                "GET", f"projects/{project_id}/tasks", access_token, org_id
            )
            tasks = response.get("tasks", [])
            _zoho_task_cache[project_id] = {
                t["task_name"].strip().lower(): t["task_id"] for t in tasks
            }
        except ZohoBooksException:
            return None

    return _zoho_task_cache[project_id].get(task_name.strip().lower())


def _create_time_entry(
    time_log,
    zoho_user_id: str,
    access_token: str,
    org_id: str,
    notes: str = "",
):
    """Create a new time entry in Zoho Books."""
    try:
        project_id = _get_project_id(time_log)

        from_time = get_datetime(time_log.from_time) if time_log.from_time else None
        to_time = get_datetime(time_log.to_time) if time_log.to_time else None
        log_date = from_time.date().isoformat() if from_time else ""

        task_id = _get_task_id(time_log, project_id, access_token, org_id)
        if not task_id:
            raise ZohoBooksException("No task ID available. Configure a Fallback Task ID in Zoho Books Settings.")

        payload = {
            "project_id": project_id,
            "task_id": task_id,
            "user_id": zoho_user_id,
            "log_date": log_date,
            "begin_time": from_time.strftime("%H:%M") if from_time else "",
            "end_time": to_time.strftime("%H:%M") if to_time else "",
            "notes": notes,
            "bill_status": "billable" if time_log.is_billable else "non_billable",
        }

        response = _make_api_request("POST", "projects/timeentries", access_token, org_id, payload)

        # Extract entry ID from response and persist to DB
        timelog_data = response.get("timelog") or response.get("time_entry") or {}
        entry_id = timelog_data.get("timelog_id") or timelog_data.get("time_entry_id")
        if entry_id and time_log.name:
            frappe.db.set_value("Timesheet Detail", time_log.name, "zoho_entry_id", entry_id)

    except Exception as e:
        raise ZohoBooksException(f"Failed to create Zoho time entry: {e}")


def _update_time_entry(
    time_log,
    zoho_user_id: str,
    access_token: str,
    org_id: str,
    notes: str = "",
):
    """Update an existing time entry in Zoho Books."""
    if not time_log.zoho_entry_id:
        # If no ID, create instead
        _create_time_entry(time_log, zoho_user_id, access_token, org_id)
        return

    try:
        project_id = _get_project_id(time_log)

        from_time = get_datetime(time_log.from_time) if time_log.from_time else None
        to_time = get_datetime(time_log.to_time) if time_log.to_time else None
        log_date = from_time.date().isoformat() if from_time else ""

        task_id = _get_task_id(time_log, project_id, access_token, org_id)
        if not task_id:
            raise ZohoBooksException("No task ID available. Configure a Fallback Task ID in Zoho Books Settings.")

        payload = {
            "project_id": project_id,
            "task_id": task_id,
            "user_id": zoho_user_id,
            "log_date": log_date,
            "begin_time": from_time.strftime("%H:%M") if from_time else "",
            "end_time": to_time.strftime("%H:%M") if to_time else "",
            "notes": notes,
            "bill_status": "billable" if time_log.is_billable else "non_billable",
        }

        endpoint = f"projects/timeentries/{time_log.zoho_entry_id}"
        _make_api_request("PUT", endpoint, access_token, org_id, payload)

    except Exception as e:
        raise ZohoBooksException(f"Failed to update Zoho time entry: {e}")


def _delete_time_entry(
    entry_id: str,
    access_token: str,
    org_id: str,
):
    """Delete a time entry from Zoho Books."""
    try:
        endpoint = f"projects/timeentries/{entry_id}"
        _make_api_request("DELETE", endpoint, access_token, org_id)
    except Exception as e:
        raise ZohoBooksException(f"Failed to delete Zoho time entry: {e}")
