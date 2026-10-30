from __future__ import annotations

import re
from html import escape, unescape

from bs4 import BeautifulSoup, NavigableString, Tag
from frappe import _
from frappe.utils import cstr

from opero.opero_site.utils import optional_url

_EMPTY_HTML = {"", "<p></p>", "<p><br></p>", "<p><br/></p>"}
_WRAPPERS = {"html", "body", "div", "span", "article", "section"}
_HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_BOLD = {"strong", "b"}
_ITALIC = {"em", "i"}
_LEGACY_KEYS = {"heading", "paragraphs", "bullets", "links"}


def html_to_body_sections(html: str) -> list[dict]:
	"""Turn Text Editor HTML into ordered body blocks for the public site.

	Blocks keep the author's order. Paragraphs may carry bold, italic, and links.
	A paragraph that is only a link stays a button. Colour, underline, and other
	pasted styles are dropped.
	"""
	html = cstr(html).strip()
	if html.lower() in _EMPTY_HTML:
		return []
	soup = BeautifulSoup(html, "html.parser")
	blocks = _dedupe_mirrored(_walk_blocks(soup.children))
	folded = _fold_blocks(blocks)
	if folded is None:
		return blocks
	return dedupe_body_sections(folded)


def body_sections_to_html(sections) -> str:
	"""Turn body blocks, or the older section bags, into Text Editor HTML."""
	parts = []
	for section in dedupe_body_sections(sections) or []:
		if not isinstance(section, dict):
			continue
		if section.get("type"):
			parts.append(_block_to_html(section))
			continue
		parts.append(_legacy_section_to_html(section))
	return "".join(parts)


def dedupe_body_sections(sections) -> list[dict]:
	"""Drop an exact mirrored repeat (A+B+C + A+B+C) or consecutive identical sections."""
	rows = _dedupe_mirrored(sections)
	out = []
	for section in rows:
		if out and out[-1] == section:
			continue
		out.append(section)
	return out


def _dedupe_mirrored(sections) -> list[dict]:
	rows = [section for section in (sections or []) if isinstance(section, dict)]
	n = len(rows)
	if n >= 2 and n % 2 == 0:
		half = n // 2
		if rows[:half] == rows[half:]:
			return rows[:half]
	return rows


def _fold_blocks(blocks: list[dict]) -> list[dict] | None:
	"""Return the older section bags when that shape still shows the same article.

	A heading starts a section. Paragraphs, then a bullet list, then button links
	can share it. Bold, italic, a link inside a sentence, a numbered list, a
	heading 3, or a list that sits between paragraphs stay as ordered blocks.
	"""
	sections = []
	current: dict = {}
	stage = "paragraphs"

	def flush() -> None:
		nonlocal current, stage
		if current:
			sections.append(current)
		current = {}
		stage = "paragraphs"

	for block in blocks:
		kind = cstr(block.get("type")).strip()
		if kind == "heading":
			if int(block.get("level") or 2) != 2:
				return None
			flush()
			current = {"heading": cstr(block.get("text")).strip()}
			continue
		if kind == "paragraph":
			if block.get("spans") or stage != "paragraphs":
				return None
			text = cstr(block.get("text")).strip()
			if text:
				current.setdefault("paragraphs", []).append(text)
			continue
		if kind == "list":
			if block.get("style") != "bullet" or stage == "links":
				return None
			items = block.get("items") or []
			if any(not isinstance(item, str) for item in items):
				return None
			current.setdefault("bullets", []).extend(items)
			stage = "bullets"
			continue
		if kind == "link":
			label = cstr(block.get("label")).strip()
			href = cstr(block.get("href")).strip()
			if not label or not href:
				continue
			current.setdefault("links", []).append({"label": label, "href": href})
			stage = "links"
			continue
		return None
	if current:
		sections.append(current)
	return sections


def normalize_body_html(html: str) -> str:
	"""Round-trip Text Editor HTML through the body blocks and drop mirrored dupes."""
	return body_sections_to_html(html_to_body_sections(html))


def html_to_paragraphs(html: str) -> list[str]:
	"""Turn Text Editor HTML into a flat paragraph list for about.paragraphs."""
	paragraphs = []
	for block in html_to_body_sections(html):
		if block.get("type") == "paragraph":
			text = _plain_spans(_paragraph_spans(block)).strip()
			if text:
				paragraphs.append(text)
			continue
		if block.get("type"):
			continue
		for para in block.get("paragraphs") or []:
			text = cstr(para).strip()
			if text:
				paragraphs.append(text)
	return dedupe_paragraphs(paragraphs)


def paragraphs_to_html(paragraphs) -> str:
	"""Turn a paragraph list into Text Editor HTML."""
	parts = []
	for para in dedupe_paragraphs(paragraphs):
		parts.append(f"<p>{escape(para)}</p>")
	return "".join(parts)


def dedupe_paragraphs(paragraphs) -> list[str]:
	"""Drop an exact mirrored repeat (A+B + A+B)."""
	rows = [cstr(para).strip() for para in (paragraphs or []) if cstr(para).strip()]
	n = len(rows)
	if n >= 2 and n % 2 == 0:
		half = n // 2
		if rows[:half] == rows[half:]:
			return rows[:half]
	return rows


def normalize_paragraphs_html(html: str) -> str:
	"""Round-trip Text Editor HTML through the about.paragraphs model."""
	return paragraphs_to_html(html_to_paragraphs(html))


def _legacy_section_to_html(section: dict) -> str:
	if not _LEGACY_KEYS.intersection(section):
		return ""
	parts = []
	heading = cstr(section.get("heading")).strip()
	if heading:
		parts.append(f"<h2>{escape(heading)}</h2>")
	for para in section.get("paragraphs") or []:
		text = cstr(para).strip()
		if text:
			parts.append(f"<p>{escape(text)}</p>")
	bullets = [cstr(item).strip() for item in (section.get("bullets") or []) if cstr(item).strip()]
	if bullets:
		items = "".join(f"<li>{escape(item)}</li>" for item in bullets)
		parts.append(f"<ul>{items}</ul>")
	for link in section.get("links") or []:
		if not isinstance(link, dict):
			continue
		label = cstr(link.get("label")).strip()
		href = cstr(link.get("href") or link.get("url")).strip()
		if label and href:
			parts.append(f'<p><a href="{escape(href, quote=True)}">{escape(label)}</a></p>')
	return "".join(parts)


def _block_to_html(block: dict) -> str:
	kind = cstr(block.get("type")).strip()
	if kind == "heading":
		text = cstr(block.get("text")).strip()
		if not text:
			return ""
		level = 3 if int(block.get("level") or 2) == 3 else 2
		return f"<h{level}>{escape(text)}</h{level}>"
	if kind == "paragraph":
		inner = _spans_to_html(_paragraph_spans(block))
		return f"<p>{inner}</p>" if inner else ""
	if kind == "list":
		tag = "ol" if block.get("style") == "number" else "ul"
		items = []
		for item in block.get("items") or []:
			inner = _spans_to_html(_item_spans(item))
			if inner:
				items.append(f"<li>{inner}</li>")
		if not items:
			return ""
		return f"<{tag}>{''.join(items)}</{tag}>"
	if kind == "link":
		label = cstr(block.get("label")).strip()
		href = cstr(block.get("href")).strip()
		if label and href:
			return f'<p><a href="{escape(href, quote=True)}">{escape(label)}</a></p>'
	return ""


def _paragraph_spans(block: dict) -> list[dict]:
	spans = block.get("spans")
	if isinstance(spans, list) and spans:
		return [span for span in spans if isinstance(span, dict)]
	text = cstr(block.get("text")).strip()
	return [{"text": text}] if text else []


def _item_spans(item) -> list[dict]:
	if isinstance(item, str):
		text = item.strip()
		return [{"text": text}] if text else []
	if isinstance(item, dict):
		return _paragraph_spans(item)
	if isinstance(item, list):
		return [span for span in item if isinstance(span, dict)]
	return []


def _spans_to_html(spans: list[dict]) -> str:
	parts = []
	for span in spans:
		text = escape(cstr(span.get("text")))
		if not text:
			continue
		if span.get("italic"):
			text = f"<em>{text}</em>"
		if span.get("bold"):
			text = f"<strong>{text}</strong>"
		href = cstr(span.get("href")).strip()
		if href:
			text = f'<a href="{escape(href, quote=True)}">{text}</a>'
		parts.append(text)
	return "".join(parts)


def _plain_spans(spans: list[dict]) -> str:
	return "".join(cstr(span.get("text")) for span in spans)


def _walk_blocks(nodes) -> list[dict]:
	blocks = []
	for node in nodes:
		if isinstance(node, Tag):
			blocks.extend(_blocks_from_tag(node))
			continue
		if isinstance(node, NavigableString):
			blocks.extend(_paragraph_blocks(_collect_spans(node)))
	return blocks


def _blocks_from_tag(tag: Tag) -> list[dict]:
	name = (tag.name or "").lower()
	if _is_quill_chrome(tag) or name in {"br", "hr"}:
		return []
	if name in _WRAPPERS or name == "blockquote":
		return _walk_blocks(tag.children)
	if name in _HEADINGS:
		text = _plain_spans(_trim_spans(_merge_spans(_collect_spans(tag)))).strip()
		if not text:
			return []
		level = 3 if name in {"h3", "h4", "h5", "h6"} else 2
		return [{"type": "heading", "level": level, "text": text}]
	if name == "p":
		return _blocks_from_paragraph(tag)
	if name in {"ul", "ol"}:
		return _blocks_from_list(tag)
	if name == "a":
		return _link_blocks(tag)
	if name in _BOLD | _ITALIC | {"u"}:
		return _paragraph_blocks(_collect_spans(tag))
	return _walk_blocks(tag.children)


def _blocks_from_paragraph(tag: Tag) -> list[dict]:
	if _is_links_only(tag):
		blocks = []
		for anchor in tag.find_all("a"):
			blocks.extend(_link_blocks(anchor))
		return blocks
	return _paragraph_blocks(_collect_spans(tag))


def _link_blocks(tag: Tag) -> list[dict]:
	label = _plain_spans(_trim_spans(_merge_spans(_collect_spans(tag)))).strip()
	href = cstr(tag.get("href")).strip()
	if not label or not href:
		return []
	return [{"type": "link", "label": label, "href": _body_link_url(href, label)}]


def _blocks_from_list(tag: Tag) -> list[dict]:
	groups: list[list] = []
	for item in tag.find_all("li", recursive=False):
		spans = _item_spans_from_li(item)
		if spans:
			style = _list_style(item, tag)
			if groups and groups[-1][0] == style:
				groups[-1][1].append(spans)
			else:
				groups.append([style, [spans]])
		for nested in item.find_all(["ul", "ol"], recursive=False):
			for block in _blocks_from_list(nested):
				style = block.get("style")
				items = block.get("items") or []
				if groups and groups[-1][0] == style:
					groups[-1][1].extend(items)
				else:
					groups.append([style, list(items)])
	blocks = []
	for style, items in groups:
		if items:
			blocks.append({"type": "list", "style": style, "items": items})
	return blocks


def _item_spans_from_li(tag: Tag) -> list[dict] | str:
	spans = []
	for child in tag.children:
		if isinstance(child, Tag) and (child.name or "").lower() in {"ul", "ol"}:
			continue
		spans.extend(_collect_spans(child))
	return _compact_spans(spans)


def _list_style(item: Tag, parent: Tag) -> str:
	kind = cstr(item.get("data-list")).strip().lower()
	if kind in {"ordered", "number"}:
		return "number"
	if kind in {"bullet", "checked", "unchecked"}:
		return "bullet"
	return "number" if (parent.name or "").lower() == "ol" else "bullet"


def _paragraph_blocks(spans: list[dict]) -> list[dict]:
	compact = _compact_spans(spans)
	if not compact:
		return []
	if isinstance(compact, str):
		return [{"type": "paragraph", "text": compact}]
	return [{"type": "paragraph", "spans": compact}]


def _compact_spans(spans: list[dict]) -> list[dict] | str:
	trimmed = _trim_spans(_merge_spans(spans))
	if not trimmed:
		return []
	if len(trimmed) == 1 and list(trimmed[0]) == ["text"]:
		return trimmed[0]["text"]
	return trimmed


def _collect_spans(node, bold: bool = False, italic: bool = False, href: str = "") -> list[dict]:
	if isinstance(node, NavigableString):
		text = unescape(cstr(node).replace("\xa0", " "))
		if not text:
			return []
		return [_span(text, bold, italic, href)]
	if not isinstance(node, Tag) or _is_quill_chrome(node):
		return []
	name = (node.name or "").lower()
	if name in {"ul", "ol"}:
		return []
	if name == "br":
		return [_span(" ", bold, italic, href)]
	if name in {"hr", "script", "style"}:
		return []
	if name in _BOLD:
		bold = True
	if name in _ITALIC:
		italic = True
	if name == "a":
		href = cstr(node.get("href")).strip()
	spans = []
	for child in node.children:
		spans.extend(_collect_spans(child, bold, italic, href))
	return spans


def _span(text: str, bold: bool, italic: bool, href: str) -> dict:
	span = {"text": text}
	if bold:
		span["bold"] = True
	if italic:
		span["italic"] = True
	if href:
		span["href"] = _body_link_url(href, text)
	return span


def _merge_spans(spans: list[dict]) -> list[dict]:
	merged = []
	for span in spans:
		text = cstr(span.get("text"))
		if not text:
			continue
		key = (bool(span.get("bold")), bool(span.get("italic")), cstr(span.get("href")))
		if merged and merged[-1][0] == key:
			merged[-1][1]["text"] += text
			continue
		item = {"text": text}
		if key[0]:
			item["bold"] = True
		if key[1]:
			item["italic"] = True
		if key[2]:
			item["href"] = key[2]
		merged.append((key, item))
	return [item for _, item in merged]


def _trim_spans(spans: list[dict]) -> list[dict]:
	rows = [dict(span) for span in spans if cstr(span.get("text"))]
	if not rows:
		return []
	rows[0]["text"] = rows[0]["text"].lstrip()
	rows[-1]["text"] = rows[-1]["text"].rstrip()
	return _merge_spans(rows)


def _is_links_only(tag: Tag) -> bool:
	if not tag.find("a"):
		return False
	clone = BeautifulSoup(str(tag), "html.parser")
	for element in clone.find_all(["a", "br"]):
		element.decompose()
	return not clone.get_text(strip=True)


def _is_quill_chrome(tag: Tag) -> bool:
	classes = tag.get("class") or []
	if isinstance(classes, str):
		classes = classes.split()
	return "ql-ui" in classes


def _body_link_url(href: str, text: str) -> str:
	# Quill accepts addresses without a scheme; complete explicit www addresses.
	if re.fullmatch(r"www\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:[/\?#][^\s]*)?", href):
		href = "https://" + href
	return optional_url(
		href,
		_("Body link"),
		invalid_message=_(
			"“{0}” has an invalid link. Edit this link in Body: use an address starting with https://, or remove the link."
		).format(escape(text.strip()[:100])),
	)
