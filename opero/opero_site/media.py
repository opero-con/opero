from __future__ import annotations

import hashlib
import os
from urllib.parse import unquote, urlparse

import frappe
from frappe import _
from frappe.utils import cstr, get_files_path
from frappe.utils.file_manager import is_safe_path

from opero.opero_site.markdown import split_markdown, to_markdown

_DESK_PREFIXES = ("/private/files/", "/files/")


def git_blob_sha(content: bytes) -> str:
	return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()


def desk_file_url(value: str) -> str | None:
	raw = cstr(value).strip()
	if not raw:
		return None
	path = urlparse(raw).path if "://" in raw else raw.split("?", 1)[0]
	path = unquote(path)
	if path.startswith(_DESK_PREFIXES):
		return path
	return None


def media_folder_for(path: str) -> str:
	if path == "content/homepage/home.md":
		return "homepage"
	if path.startswith("content/publications/"):
		return "publications"
	if path.startswith("content/team/"):
		return "team"
	if path == "content/settings/general.md":
		return "og"
	return "uploads"


def export_markdown_media(path: str, text: str) -> tuple[str, list[tuple[str, bytes]]]:
	"""Rewrite Desk file URLs to `/media/...` and return those files as git blobs."""
	try:
		data, body = split_markdown(text)
	except ValueError:
		return text, []
	attachments: list[tuple[str, bytes]] = []
	rewritten = _rewrite(data, media_folder_for(path), attachments)
	return to_markdown(rewritten, body), attachments


def export_planned_media(planned: list[tuple[str, str]]) -> tuple[list[tuple[str, str]], list[tuple[str, bytes]]]:
	rewritten = []
	media: list[tuple[str, bytes]] = []
	seen: dict[str, bytes] = {}
	for path, content in planned:
		text, attachments = export_markdown_media(path, content)
		rewritten.append((path, text))
		for repo_path, blob in attachments:
			existing = seen.get(repo_path)
			if existing is None:
				seen[repo_path] = blob
				media.append((repo_path, blob))
			elif existing != blob:
				frappe.throw(_("Two attachments would publish to {0} with different contents.").format(repo_path))
	return rewritten, media


def _rewrite(value, folder: str, attachments: list[tuple[str, bytes]]):
	if isinstance(value, dict):
		return {key: _rewrite(item, folder, attachments) for key, item in value.items()}
	if isinstance(value, list):
		return [_rewrite(item, folder, attachments) for item in value]
	if isinstance(value, str):
		return _rewrite_url(value, folder, attachments)
	return value


def _rewrite_url(value: str, folder: str, attachments: list[tuple[str, bytes]]) -> str:
	file_url = desk_file_url(value)
	if not file_url:
		return value
	repo_path = f"media/{folder}/{_safe_filename(file_url)}"
	blob = read_desk_file(file_url)
	attachments.append((repo_path, blob))
	return f"/{repo_path}"


def _safe_filename(file_url: str) -> str:
	name = os.path.basename(file_url).strip()
	if not name or name in (".", "..") or "/" in name or "\\" in name or "\x00" in name:
		frappe.throw(_("Cannot publish an attachment with an unsafe filename."))
	return name


def read_desk_file(file_url: str) -> bytes:
	relative = _relative_files_path(file_url)
	is_private = file_url.startswith("/private/files/")
	disk_path = get_files_path(*relative.split("/"), is_private=1 if is_private else 0)
	if not is_safe_path(disk_path) or not os.path.isfile(disk_path):
		frappe.throw(_("Cannot publish {0}: the file is not on this site.").format(file_url))
	with open(disk_path, "rb") as handle:
		return handle.read()


def _relative_files_path(file_url: str) -> str:
	if file_url.startswith("/private/files/"):
		relative = file_url[len("/private/files/") :]
	else:
		relative = file_url[len("/files/") :]
	parts = [part for part in relative.split("/") if part]
	if not parts or any(part in (".", "..") for part in parts):
		frappe.throw(_("Cannot publish {0}: the file is not on this site.").format(file_url))
	return "/".join(parts)
