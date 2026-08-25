from __future__ import annotations

import re

import yaml


def to_markdown(frontmatter: dict) -> str:
	payload = yaml.safe_dump(
		frontmatter,
		sort_keys=False,
		allow_unicode=True,
		default_flow_style=False,
	)
	return f"---\n{payload}---\n"


def parse_frontmatter(text: str) -> dict:
	match = re.match(r"^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n[\s\S]*)?$", text)
	if not match:
		raise ValueError("Markdown is missing YAML frontmatter.")
	data = yaml.safe_load(match.group(1))
	if not isinstance(data, dict):
		raise ValueError("Frontmatter must be a mapping.")
	return data
