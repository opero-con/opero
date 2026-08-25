from __future__ import annotations

import yaml


def to_markdown(frontmatter: dict) -> str:
	payload = yaml.safe_dump(
		frontmatter,
		sort_keys=False,
		allow_unicode=True,
		default_flow_style=False,
	)
	return f"---\n{payload}---\n"
