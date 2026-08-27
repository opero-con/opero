from __future__ import annotations

import base64
from urllib.parse import quote

import requests
from frappe import _

from opero.opero_site.markdown import same_managed_content


class GithubError(Exception):
	pass


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
		try:
			payload = self._api("GET", f"/repos/{self.repo}/contents/{quote(path)}?ref={quote(ref)}")
		except GithubError as exc:
			if "404" in str(exc):
				return None
			raise
		encoded = payload.get("content")
		if not encoded:
			return None
		return base64.b64decode(encoded.replace("\n", "")).decode("utf-8")

	def existing_files(self, paths: list[str], ref: str, on_progress=None) -> dict[str, str]:
		out = {}
		total = len(paths)
		for index, path in enumerate(paths, start=1):
			content = self.get_file(path, ref)
			if content is not None:
				out[path] = content
			if on_progress:
				on_progress(index, total, path)
		return out

	def list_markdown(self, prefix: str, ref: str) -> list[str]:
		head = self._api("GET", f"/repos/{self.repo}/commits/{ref}")
		tree = self._api(
			"GET",
			f"/repos/{self.repo}/git/trees/{head['commit']['tree']['sha']}?recursive=1",
		)
		if tree.get("truncated"):
			raise GithubError(_("GitHub tree listing was truncated."))
		return [
			entry["path"]
			for entry in tree.get("tree", [])
			if entry.get("type") == "blob"
			and entry.get("path", "").startswith(prefix)
			and entry["path"].endswith(".md")
		]

	def commit_files(self, files: list[tuple[str, str | None]], message: str, on_progress=None) -> dict:
		head = self._api("GET", f"/repos/{self.repo}/commits/{self.base_branch}")
		base_sha = head["sha"]
		entries = []
		total = len(files)
		for index, (path, content) in enumerate(files, start=1):
			if content is None:
				entries.append({"path": path, "mode": "100644", "type": "blob", "sha": None})
			else:
				blob = self._api(
					"POST",
					f"/repos/{self.repo}/git/blobs",
					json={"content": content, "encoding": "utf-8"},
				)
				entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
			if on_progress:
				on_progress(index, total, path)
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
