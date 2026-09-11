from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

import frappe
import requests
from frappe import _

from opero.opero_site.markdown import same_managed_content

MAX_CONCURRENT_REQUESTS = 8
BLOB_CACHE_PREFIX = "opero_content_blob"
BLOB_CACHE_TTL = 60 * 60 * 24 * 30


class GithubError(Exception):
	pass


def _cached_blob(sha: str) -> str | None:
	return frappe.cache.get_value(f"{BLOB_CACHE_PREFIX}:{sha}")


def _cache_blob(sha: str, content: str) -> None:
	frappe.cache.set_value(f"{BLOB_CACHE_PREFIX}:{sha}", content, expires_in_sec=BLOB_CACHE_TTL)


def map_concurrently(paths: list[str], worker, on_progress=None) -> dict[str, object]:
	"""Run worker(path) for each path on a small thread pool, keyed by path."""
	results: dict[str, object] = {}
	if not paths:
		return results
	total = len(paths)
	done = 0
	with ThreadPoolExecutor(max_workers=min(MAX_CONCURRENT_REQUESTS, total)) as pool:
		futures = {pool.submit(worker, path): path for path in paths}
		for future in as_completed(futures):
			path = futures[future]
			results[path] = future.result()
			done += 1
			if on_progress:
				on_progress(done, total, path)
	return results


def changed_files(existing: dict[str, str], planned: list[tuple[str, str]]) -> list[tuple[str, str]]:
	out = []
	for path, content in planned:
		current = existing.get(path)
		if current is None:
			out.append((path, content))
		elif not same_managed_content(path, current, content):
			out.append((path, content))
	return out


def deleted_managed_files(
	planned_paths: list[str],
	remote_paths: list[str],
	prefixes: tuple[str, ...],
) -> list[tuple[str, None]]:
	planned = set(planned_paths)
	return [
		(path, None)
		for path in remote_paths
		if path not in planned and path.startswith(prefixes)
	]


class ContentRepo:
	def __init__(self, token: str, repo: str, base_branch: str = "main", transport=None):
		self.token = token
		self.repo = repo
		self.base_branch = base_branch
		self._transport = transport or self._http
		self._tree_blobs: dict[str, dict[str, str]] = {}

	def _headers(self) -> dict:
		return {
			"Authorization": f"Bearer {self.token}",
			"Accept": "application/vnd.github+json",
			"X-GitHub-Api-Version": "2022-11-28",
		}

	def _http(self, method: str, url: str, json=None):
		response = requests.request(method, url, headers=self._headers(), json=json, timeout=30)
		if response.status_code >= 400:
			raise GithubError(_("GitHub {0} failed ({1}).").format(method, response.status_code))
		if response.status_code == 204 or not response.content:
			return {}
		return response.json()

	def _api(self, method: str, path: str, json=None):
		return self._transport(method, f"https://api.github.com{path}", json=json)

	def get_file(self, path: str, ref: str) -> str | None:
		raw = self.get_bytes(path, ref)
		if raw is None:
			return None
		return raw.decode("utf-8")

	def get_bytes(self, path: str, ref: str) -> bytes | None:
		try:
			payload = self._api("GET", f"/repos/{self.repo}/contents/{quote(path)}?ref={quote(ref)}")
		except GithubError as exc:
			if "404" in str(exc):
				return None
			raise
		encoded = payload.get("content")
		if not encoded:
			return None
		return base64.b64decode(encoded.replace("\n", ""))

	def existing_files(self, paths: list[str], ref: str, on_progress=None) -> dict[str, str]:
		"""Current content for `paths`, served from a blob-sha cache where possible.

		The repo tree (already fetched for `tree_blobs`) gives each path's current
		blob sha for free, so only paths whose sha isn't cached need a GitHub round
		trip, and those go out concurrently.
		"""
		if not paths:
			return {}
		blobs = self.tree_blobs(ref)
		out: dict[str, str] = {}
		to_fetch = []
		for path in paths:
			sha = blobs.get(path)
			cached = _cached_blob(sha) if sha else None
			if cached is not None:
				out[path] = cached
			else:
				to_fetch.append(path)
		fetched = map_concurrently(to_fetch, lambda path: self.get_file(path, ref), on_progress=on_progress)
		for path, content in fetched.items():
			if content is None:
				continue
			out[path] = content
			sha = blobs.get(path)
			if sha:
				_cache_blob(sha, content)
		return out

	def tree_blobs(self, ref: str) -> dict[str, str]:
		cached = self._tree_blobs.get(ref)
		if cached is not None:
			return cached
		head = self._api("GET", f"/repos/{self.repo}/commits/{ref}")
		tree = self._api(
			"GET",
			f"/repos/{self.repo}/git/trees/{head['commit']['tree']['sha']}?recursive=1",
		)
		if tree.get("truncated"):
			raise GithubError(_("GitHub tree listing was truncated."))
		blobs = {
			entry["path"]: entry.get("sha") or ""
			for entry in tree.get("tree", [])
			if entry.get("type") == "blob" and entry.get("path")
		}
		self._tree_blobs[ref] = blobs
		return blobs

	def list_markdown(self, prefix: str, ref: str) -> list[str]:
		return [
			path
			for path in self.tree_blobs(ref)
			if path.startswith(prefix) and path.endswith(".md")
		]

	def commit_files(self, files: list[tuple[str, str | bytes | None]], message: str, on_progress=None) -> dict:
		head = self._api("GET", f"/repos/{self.repo}/commits/{self.base_branch}")
		base_sha = head["sha"]
		content_by_path = {path: content for path, content in files if content is not None}
		blob_shas = map_concurrently(
			list(content_by_path),
			lambda path: self._api(
				"POST", f"/repos/{self.repo}/git/blobs", json=_blob_payload(content_by_path[path])
			)["sha"],
			on_progress=on_progress,
		)
		entries = [
			{"path": path, "mode": "100644", "type": "blob", "sha": blob_shas.get(path)}
			for path, _content in files
		]
		tree = self._api(
			"POST",
			f"/repos/{self.repo}/git/trees",
			json={"base_tree": head["commit"]["tree"]["sha"], "tree": entries},
		)
		commit = self._api(
			"POST",
			f"/repos/{self.repo}/git/commits",
			json={"message": message, "tree": tree["sha"], "parents": [base_sha]},
		)
		self._api(
			"PATCH",
			f"/repos/{self.repo}/git/refs/heads/{quote(self.base_branch)}",
			json={"sha": commit["sha"], "force": False},
		)
		sha = commit["sha"]
		return {"sha": sha, "html_url": f"https://github.com/{self.repo}/commit/{sha}"}


def _blob_payload(content: str | bytes) -> dict:
	if isinstance(content, bytes):
		return {"content": base64.b64encode(content).decode("ascii"), "encoding": "base64"}
	return {"content": content, "encoding": "utf-8"}
