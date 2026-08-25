from __future__ import annotations

import base64
from urllib.parse import quote

import requests
from frappe import _


class GithubError(Exception):
	pass


def changed_files(existing: dict[str, str], planned: list[tuple[str, str]]) -> list[tuple[str, str]]:
	return [(path, content) for path, content in planned if existing.get(path) != content]


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

	def existing_files(self, paths: list[str], ref: str) -> dict[str, str]:
		out = {}
		for path in paths:
			content = self.get_file(path, ref)
			if content is not None:
				out[path] = content
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

	def open_content_pr(self, files: list[tuple[str, str]], branch: str, title: str, body: str) -> str:
		head = self._api("GET", f"/repos/{self.repo}/commits/{self.base_branch}")
		base_sha = head["sha"]
		entries = []
		for path, content in files:
			blob = self._api(
				"POST",
				f"/repos/{self.repo}/git/blobs",
				json={"content": content, "encoding": "utf-8"},
			)
			entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
		tree = self._api(
			"POST",
			f"/repos/{self.repo}/git/trees",
			json={"base_tree": head["commit"]["tree"]["sha"], "tree": entries},
		)
		commit = self._api(
			"POST",
			f"/repos/{self.repo}/git/commits",
			json={"message": title, "tree": tree["sha"], "parents": [base_sha]},
		)
		self._api(
			"POST",
			f"/repos/{self.repo}/git/refs",
			json={"ref": f"refs/heads/{branch}", "sha": commit["sha"]},
		)
		pull = self._api(
			"POST",
			f"/repos/{self.repo}/pulls",
			json={"title": title, "head": branch, "base": self.base_branch, "body": body},
		)
		return pull["html_url"]
