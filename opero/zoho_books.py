"""Zoho Books integration for Cubenet timesheets."""

from __future__ import annotations

import frappe
import requests
from datetime import datetime, timedelta
from frappe.utils import get_datetime, get_url
from typing import Optional, Dict, Any


class ZohoBooksException(Exception):
	pass


ZOHO_OAUTH_CALLBACK_PATH = "/api/method/opero.zoho_books.oauth_callback"
_INTEGRATION = "zoho_books"


# : Mapping registry helpers

def _get_mapping(entity_type: str, local_name: str) -> Optional[str]:
	return frappe.db.get_value(
		"Integration Mapping",
		{"integration": _INTEGRATION, "entity_type": entity_type, "local_name": local_name},
		"remote_id",
	)


def _set_mapping(entity_type: str, local_name: str, remote_id: str, remote_name: str = "") -> None:
	existing = frappe.db.get_value(
		"Integration Mapping",
		{"integration": _INTEGRATION, "entity_type": entity_type, "local_name": local_name},
		"name",
	)
	if existing:
		frappe.db.set_value("Integration Mapping", existing, {"remote_id": remote_id, "remote_name": remote_name})
	else:
		frappe.get_doc({
			"doctype": "Integration Mapping",
			"integration": _INTEGRATION,
			"entity_type": entity_type,
			"local_name": local_name,
			"remote_id": remote_id,
			"remote_name": remote_name,
		}).insert(ignore_permissions=True)


def _delete_mapping(entity_type: str, local_name: str) -> None:
	name = frappe.db.get_value(
		"Integration Mapping",
		{"integration": _INTEGRATION, "entity_type": entity_type, "local_name": local_name},
		"name",
	)
	if name:
		frappe.delete_doc("Integration Mapping", name, ignore_permissions=True)


# : Sync entry points

def sync_timesheet_to_zoho(doc, method: str = "submit"):
	if method == "on_cancel":
		_delete_timesheet_entries(doc)
	elif method == "on_amend":
		_sync_timesheet_entries(doc, is_update=True)
	else:
		_sync_timesheet_entries(doc, is_update=False)


def _sync_timesheet_entries(doc, is_update: bool = False):
	try:
		settings = _get_settings()
		if not settings or not settings.enabled:
			frappe.logger().info(f"Zoho Books: sync skipped for {doc.name} — integration not enabled")
			return

		_validate_settings(settings)
		access_token = _get_or_refresh_token(settings)
		org_id = settings.organization_id

		zoho_user_id = _get_mapping("Employee", doc.employee)
		if not zoho_user_id:
			frappe.msgprint(
				f"Zoho Books: No personnel mapping found for <b>{doc.employee}</b>. "
				"Add a mapping in Zoho Books Settings → Personnel Mapping.",
				indicator="orange",
				alert=True,
			)
			frappe.log_error(
				f"Zoho Books sync skipped — no personnel mapping for employee '{doc.employee}' on timesheet {doc.name}",
				"Zoho Books Sync"
			)
			return

		ts_note = frappe.utils.strip_html(doc.note or "") if getattr(doc, "note", None) else ""
		errors = []
		for time_log in doc.time_logs:
			try:
				notes = getattr(time_log, "description", None) or ts_note
				existing_entry_id = _get_mapping("Timesheet Detail", time_log.name)
				if is_update and existing_entry_id:
					_update_time_entry(time_log, zoho_user_id, access_token, org_id, notes, existing_entry_id)
				else:
					_create_time_entry(time_log, zoho_user_id, access_token, org_id, notes)
			except ZohoBooksException as e:
				frappe.logger().error(f"Failed to sync time log: {e}")
				errors.append(str(e))

		count = len(doc.time_logs) - len(errors)
		if errors:
			frappe.msgprint(
				f"Zoho Books: {count} of {len(doc.time_logs)} entries synced.<br>"
				+ "<br>".join(errors),
				indicator="red",
				alert=True,
			)
		else:
			frappe.msgprint(
				f"Zoho Books: {count} time entries synced successfully.",
				indicator="green",
				alert=True,
			)

	except ZohoBooksException as e:
		frappe.msgprint(f"Zoho Books sync failed: {e}", indicator="red", alert=True)


def _delete_timesheet_entries(doc):
	try:
		settings = _get_settings()
		if not settings or not settings.enabled:
			return

		_validate_settings(settings)
		access_token = _get_or_refresh_token(settings)
		org_id = settings.organization_id

		for time_log in doc.time_logs:
			entry_id = _get_mapping("Timesheet Detail", time_log.name)
			if entry_id:
				try:
					_delete_time_entry(entry_id, access_token, org_id)
					_delete_mapping("Timesheet Detail", time_log.name)
				except ZohoBooksException as e:
					frappe.logger().error(f"Failed to delete time entry: {e}")

	except ZohoBooksException as e:
		frappe.logger().error(f"Failed to delete timesheet entries: {e}")


# : OAuth

@frappe.whitelist(allow_guest=True)
def oauth_callback():
	code = frappe.request.args.get("code")
	error = frappe.request.args.get("error")

	if error:
		frappe.respond_as_web_page("Zoho Auth Failed", f"<p>Zoho returned error: {error}</p>", http_status_code=400)
		return

	if not code:
		frappe.respond_as_web_page("Zoho Auth Failed", "<p>No authorization code received.</p>", http_status_code=400)
		return

	settings = frappe.get_doc("Zoho Books Settings")

	try:
		response = requests.post(
			settings.token_uri,
			data={
				"grant_type": "authorization_code",
				"code": code,
				"client_id": settings.client_id,
				"client_secret": settings.get_password("client_secret"),
				"redirect_uri": _get_redirect_uri(),
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
			"<p>Zoho Books connected successfully. You can close this tab.</p>",
		)

	except requests.RequestException as e:
		frappe.respond_as_web_page("Zoho Auth Failed", f"<p>Request failed: {e}</p>", http_status_code=500)


@frappe.whitelist()
def get_authorization_url():
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


# : Zoho data fetch

@frappe.whitelist()
def get_zoho_users():
	settings = _get_settings()
	_validate_settings(settings)
	access_token = _get_or_refresh_token(settings)
	response = _make_api_request("GET", "users", access_token, settings.organization_id)
	return response.get("users", [])


@frappe.whitelist()
def test_sync_timesheet(timesheet_name):
	"""Manually trigger Zoho sync for a submitted timesheet — for diagnosing silent failures."""
	doc = frappe.get_doc("Timesheet", timesheet_name)
	if doc.docstatus != 1:
		frappe.throw(f"Timesheet {timesheet_name} is not submitted (docstatus={doc.docstatus})")
	_sync_timesheet_entries(doc, is_update=False)
	return {"status": "done"}


@frappe.whitelist()
def debug_project_tasks(project):
	"""Returns raw Zoho API response for a project's tasks — for diagnosing mapping issues."""
	zoho_project_id = _get_mapping("Project", project)
	if not zoho_project_id:
		return {"error": f"No Zoho mapping found for project '{project}'"}
	settings = _get_settings()
	_validate_settings(settings)
	access_token = _get_or_refresh_token(settings)
	response = _make_api_request("GET", f"projects/{zoho_project_id}/tasks", access_token, settings.organization_id)
	return {"zoho_project_id": zoho_project_id, "response": response}


@frappe.whitelist()
def get_zoho_projects():
	settings = _get_settings()
	_validate_settings(settings)
	access_token = _get_or_refresh_token(settings)
	response = _make_api_request("GET", "projects", access_token, settings.organization_id)
	return response.get("projects", [])


# : Mapping read/write (whitelisted for UI)

@frappe.whitelist()
def get_unmapped_employees():
	"""Return Employees not yet mapped in Integration Mapping."""
	mapped = set(frappe.db.get_all(
		"Integration Mapping",
		filters={"integration": _INTEGRATION, "entity_type": "Employee"},
		pluck="local_name",
	) or [])
	all_employees = frappe.db.get_all(
		"Employee",
		fields=["name", "employee_name"],
		order_by="employee_name asc",
	)
	return [e for e in all_employees if e.name not in mapped]


@frappe.whitelist()
def get_personnel_mappings():
	return frappe.db.get_all(
		"Integration Mapping",
		filters={"integration": _INTEGRATION, "entity_type": "Employee"},
		fields=["name", "local_name", "remote_id", "remote_name"],
	)


@frappe.whitelist()
def delete_personnel_mapping(mapping_name):
	frappe.delete_doc("Integration Mapping", mapping_name, ignore_permissions=True)
	frappe.db.commit()
	return {"status": "ok"}


@frappe.whitelist()
def save_personnel_mappings(mappings):
	import json
	if isinstance(mappings, str):
		mappings = json.loads(mappings)
	saved = []
	for m in mappings:
		if m.get("local_name") and m.get("remote_id"):
			existing_remote = frappe.db.get_value(
				"Integration Mapping",
				{"integration": _INTEGRATION, "entity_type": "Employee", "local_name": m["local_name"]},
				"remote_id",
			)
			if existing_remote and existing_remote != m["remote_id"]:
				frappe.throw(f"'{m['local_name']}' is already mapped to another Zoho user. Unmap it first.")
			_set_mapping("Employee", m["local_name"], m["remote_id"], m.get("remote_name", ""))
			doc_name = frappe.db.get_value(
				"Integration Mapping",
				{"integration": _INTEGRATION, "entity_type": "Employee", "local_name": m["local_name"]},
				"name",
			)
			saved.append({"name": doc_name, "local_name": m["local_name"], "remote_id": m["remote_id"], "remote_name": m.get("remote_name", "")})
	frappe.db.commit()
	return {"status": "ok", "count": len(saved), "saved": saved}


@frappe.whitelist()
def get_unmapped_projects():
	"""Return Projects not yet mapped in Integration Mapping."""
	mapped = set(frappe.db.get_all(
		"Integration Mapping",
		filters={"integration": _INTEGRATION, "entity_type": "Project"},
		pluck="local_name",
	) or [])
	all_projects = frappe.db.get_all(
		"Project",
		fields=["name", "project_name"],
		order_by="project_name asc",
	)
	return [p for p in all_projects if p.name not in mapped]


@frappe.whitelist()
def get_project_mappings():
	return frappe.db.get_all(
		"Integration Mapping",
		filters={"integration": _INTEGRATION, "entity_type": "Project"},
		fields=["name", "local_name", "remote_id", "remote_name"],
	)


@frappe.whitelist()
def delete_project_mapping(mapping_name):
	frappe.delete_doc("Integration Mapping", mapping_name, ignore_permissions=True)
	frappe.db.commit()
	return {"status": "ok"}


@frappe.whitelist()
def delete_task_mapping(mapping_name):
	frappe.delete_doc("Integration Mapping", mapping_name, ignore_permissions=True)
	frappe.db.commit()
	return {"status": "ok"}


@frappe.whitelist()
def save_project_mappings(mappings):
	import json
	if isinstance(mappings, str):
		mappings = json.loads(mappings)
	saved = []
	for m in mappings:
		if m.get("local_name") and m.get("remote_id"):
			existing_remote = frappe.db.get_value(
				"Integration Mapping",
				{"integration": _INTEGRATION, "entity_type": "Project", "local_name": m["local_name"]},
				"remote_id",
			)
			if existing_remote and existing_remote != m["remote_id"]:
				frappe.throw(f"'{m['local_name']}' is already mapped to another Zoho project. Unmap it first.")
			_set_mapping("Project", m["local_name"], m["remote_id"], m.get("remote_name", ""))
			doc_name = frappe.db.get_value(
				"Integration Mapping",
				{"integration": _INTEGRATION, "entity_type": "Project", "local_name": m["local_name"]},
				"name",
			)
			saved.append({"name": doc_name, "local_name": m["local_name"], "remote_id": m["remote_id"], "remote_name": m.get("remote_name", "")})
	frappe.db.commit()
	return {"status": "ok", "count": len(saved), "saved": saved}


@frappe.whitelist()
def get_task_mapping_data(project):
	zoho_project_id = _get_mapping("Project", project)
	if not zoho_project_id:
		frappe.throw("This project has no Zoho mapping. Map it in the Project Mapping tab first.")

	all_cubenet_tasks = frappe.db.get_list(
		"Task",
		filters={"project": project},
		fields=["name", "subject"],
		order_by="subject asc",
	)
	cubenet_task_names = [t.name for t in all_cubenet_tasks]

	existing_mappings = frappe.db.get_all(
		"Integration Mapping",
		filters={"integration": _INTEGRATION, "entity_type": "Task", "local_name": ["in", cubenet_task_names]},
		fields=["name", "local_name", "remote_id", "remote_name"],
	) if cubenet_task_names else []

	mapped_remote_ids = {m.remote_id for m in existing_mappings}
	mapped_local_names = {m.local_name for m in existing_mappings}
	unmapped_cubenet_tasks = [t for t in all_cubenet_tasks if t.name not in mapped_local_names]

	settings = _get_settings()
	_validate_settings(settings)
	access_token = _get_or_refresh_token(settings)
	response = _make_api_request("GET", f"projects/{zoho_project_id}/tasks", access_token, settings.organization_id)

	if response.get("code") not in (None, 0):
		frappe.throw(f"Zoho API error fetching tasks: {response.get('message', response)}")

	all_zoho_tasks = response.get("task", response.get("tasks", []))
	unmapped_zoho_tasks = [t for t in all_zoho_tasks if t["task_id"] not in mapped_remote_ids]

	return {
		"unmapped_zoho_tasks": unmapped_zoho_tasks,
		"unmapped_cubenet_tasks": unmapped_cubenet_tasks,
		"existing_mappings": existing_mappings,
	}


@frappe.whitelist()
def save_task_mappings(mappings):
	import json
	if isinstance(mappings, str):
		mappings = json.loads(mappings)
	saved = []
	for m in mappings:
		if m.get("local_name") and m.get("remote_id"):
			existing_remote = frappe.db.get_value(
				"Integration Mapping",
				{"integration": _INTEGRATION, "entity_type": "Task", "local_name": m["local_name"]},
				"remote_id",
			)
			if existing_remote and existing_remote != m["remote_id"]:
				frappe.throw(f"'{m['local_name']}' is already mapped to another Zoho task. Unmap it first.")
			_set_mapping("Task", m["local_name"], m["remote_id"], m.get("remote_name", ""))
			doc_name = frappe.db.get_value(
				"Integration Mapping",
				{"integration": _INTEGRATION, "entity_type": "Task", "local_name": m["local_name"]},
				"name",
			)
			saved.append({"name": doc_name, "local_name": m["local_name"], "remote_id": m["remote_id"], "remote_name": m.get("remote_name", "")})
	frappe.db.commit()
	return {"status": "ok", "count": len(saved), "saved": saved}


# : Internal sync helpers

def _get_project_id(time_log) -> str:
	settings = _get_settings()

	if time_log.project:
		zoho_id = _get_mapping("Project", time_log.project)
		if zoho_id:
			return zoho_id

	if settings and settings.fallback_project_id:
		return settings.fallback_project_id

	raise ZohoBooksException("No Zoho project ID found. Set a Fallback Project ID in Zoho Books Settings.")


_zoho_task_cache: Dict[str, Dict[str, str]] = {}


def _get_task_id(time_log, project_id: str, access_token: str, org_id: str) -> Optional[str]:
	cubenet_task = getattr(time_log, "task", None)
	if cubenet_task:
		stored = _get_mapping("Task", cubenet_task)
		if stored:
			return stored

	if cubenet_task and project_id:
		task_name = frappe.db.get_value("Task", cubenet_task, "subject") or cubenet_task
		zoho_task_id = _match_zoho_task_by_name(project_id, task_name, access_token, org_id)
		if zoho_task_id:
			_set_mapping("Task", cubenet_task, zoho_task_id)
			return zoho_task_id

		zoho_task_id = _create_zoho_task(project_id, task_name, access_token, org_id)
		if zoho_task_id:
			_set_mapping("Task", cubenet_task, zoho_task_id)
			frappe.msgprint(
				f"Zoho Books: created new task <b>{task_name}</b> in Zoho project.",
				indicator="blue",
				alert=True,
			)
			return zoho_task_id

	settings = _get_settings()
	if settings and settings.fallback_task_id:
		return settings.fallback_task_id

	return None


def _match_zoho_task_by_name(project_id: str, task_name: str, access_token: str, org_id: str) -> Optional[str]:
	if project_id not in _zoho_task_cache:
		try:
			response = _make_api_request("GET", f"projects/{project_id}/tasks", access_token, org_id)
			tasks = response.get("task", response.get("tasks", []))
			_zoho_task_cache[project_id] = {
				t["task_name"].strip().lower(): t["task_id"] for t in tasks
			}
		except ZohoBooksException:
			return None

	return _zoho_task_cache[project_id].get(task_name.strip().lower())


def _create_zoho_task(project_id: str, task_name: str, access_token: str, org_id: str) -> Optional[str]:
	try:
		response = _make_api_request(
			"POST", f"projects/{project_id}/tasks", access_token, org_id,
			data={"task_name": task_name},
		)
		task = response.get("task", {})
		task_id = task.get("task_id")
		if task_id and project_id in _zoho_task_cache:
			_zoho_task_cache[project_id][task_name.strip().lower()] = task_id
		return task_id
	except ZohoBooksException:
		return None


def _create_time_entry(time_log, zoho_user_id: str, access_token: str, org_id: str, notes: str = ""):
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
		timelog_data = response.get("timelog") or response.get("time_entry") or {}
		entry_id = timelog_data.get("timelog_id") or timelog_data.get("time_entry_id")
		if entry_id and time_log.name:
			_set_mapping("Timesheet Detail", time_log.name, entry_id)

	except ZohoBooksException:
		raise
	except Exception as e:
		raise ZohoBooksException(f"Failed to create Zoho time entry: {e}")


def _update_time_entry(time_log, zoho_user_id: str, access_token: str, org_id: str, notes: str = "", entry_id: str = ""):
	if not entry_id:
		_create_time_entry(time_log, zoho_user_id, access_token, org_id, notes)
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

		_make_api_request("PUT", f"projects/timeentries/{entry_id}", access_token, org_id, payload)

	except Exception as e:
		raise ZohoBooksException(f"Failed to update Zoho time entry: {e}")


def _delete_time_entry(entry_id: str, access_token: str, org_id: str):
	try:
		_make_api_request("DELETE", f"projects/timeentries/{entry_id}", access_token, org_id)
	except Exception as e:
		raise ZohoBooksException(f"Failed to delete Zoho time entry: {e}")


# : Token management

def _get_redirect_uri() -> str:
	return get_url(ZOHO_OAUTH_CALLBACK_PATH)


def _save_tokens(access_token=None, refresh_token=None, token_expiry=None):
	from frappe.utils.password import set_encrypted_password
	if access_token:
		set_encrypted_password("Zoho Books Settings", "Zoho Books Settings", access_token, "access_token")
	if refresh_token:
		set_encrypted_password("Zoho Books Settings", "Zoho Books Settings", refresh_token, "refresh_token")
	if token_expiry:
		frappe.db.set_value("Zoho Books Settings", "Zoho Books Settings", "token_expiry", token_expiry)
	frappe.db.commit()


def _get_token(fieldname: str) -> str:
	from frappe.utils.password import get_decrypted_password
	try:
		return get_decrypted_password("Zoho Books Settings", "Zoho Books Settings", fieldname, raise_exception=False)
	except Exception:
		return None


def _get_settings() -> Optional[Any]:
	try:
		return frappe.get_doc("Zoho Books Settings")
	except frappe.DoesNotExistError:
		return None


def _validate_settings(settings):
	if not settings.client_id:
		raise ZohoBooksException("Zoho Books Client ID not configured")
	if not settings.client_secret:
		raise ZohoBooksException("Zoho Books Client Secret not configured")
	if not settings.organization_id:
		raise ZohoBooksException("Zoho Books Organization ID not configured")


def _get_or_refresh_token(settings) -> str:
	if _is_token_expired(settings.token_expiry):
		refresh_token = _get_token("refresh_token")
		if not refresh_token:
			raise ZohoBooksException("No refresh token available. Please reconfigure Zoho Books authentication.")
		_refresh_access_token(settings)
		settings.reload()

	return _get_token("access_token")


def _is_token_expired(token_expiry: str) -> bool:
	if not token_expiry:
		return True
	expiry_time = get_datetime(token_expiry)
	return datetime.now() >= (expiry_time - timedelta(minutes=5))


def _refresh_access_token(settings):
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
			if response.status_code == 401 or (isinstance(body, dict) and body.get("code") == 57):
				raise ZohoBooksException(
					"Zoho Books: not authorized (code 57). "
					"The connected Zoho account must be an Admin or have permission to log time on behalf of other users. "
					"Go to Zoho Books → Settings → Users & Roles and verify the account role."
				)
			raise ZohoBooksException(f"Zoho Books API error {response.status_code}: {body}")
		return response.json()

	except ZohoBooksException:
		raise
	except requests.RequestException as e:
		raise ZohoBooksException(f"Zoho Books API request failed: {e}")
