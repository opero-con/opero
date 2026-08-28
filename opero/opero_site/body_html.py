from __future__ import annotations

from html import escape, unescape

from bs4 import BeautifulSoup, NavigableString, Tag
from frappe import _
from frappe.utils import cstr

from opero.opero_site.utils import optional_url

_EMPTY_HTML = {"", "<p></p>", "<p><br></p>", "<p><br/></p>"}
_WRAPPERS = {"html", "body", "div", "span", "article", "section"}
_HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class _Builder:
	def __init__(self):
		self.sections: list[dict] = []
		self.current: dict = {}

	def flush(self) -> None:
		if self.current:
			self.sections.append(self.current)
		self.current = {}

	def heading(self, text: str) -> None:
		self.flush()
		self.current["heading"] = text

	def paragraph(self, text: str) -> None:
		self.current.setdefault("paragraphs", []).append(text)

	def bullets(self, items: list[str]) -> None:
		self.current.setdefault("bullets", []).extend(items)

	def link(self, label: str, href: str) -> None:
		self.current.setdefault("links", []).append(
			{"label": label, "href": optional_url(href, _("Link URL"))}
		)


def html_to_body_sections(html: str) -> list[dict]:
	"""Turn Text Editor HTML into the opero-content `body` list."""
	html = cstr(html).strip()
	if html.lower() in _EMPTY_HTML:
		return []
	soup = BeautifulSoup(html, "html.parser")
	builder = _Builder()
	_walk(builder, soup.children)
	builder.flush()
	return builder.sections


def body_sections_to_html(sections) -> str:
	"""Turn the opero-content `body` list into Text Editor HTML."""
	parts = []
	for section in sections or []:
		if not isinstance(section, dict):
			continue
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


def _walk(builder: _Builder, nodes) -> None:
	for node in nodes:
		if isinstance(node, Tag):
			_walk_tag(builder, node)
			continue
		if isinstance(node, NavigableString):
			text = _text_of(node)
			if text:
				builder.paragraph(text)


def _walk_tag(builder: _Builder, tag: Tag) -> None:
	name = (tag.name or "").lower()
	if name in _WRAPPERS:
		_walk(builder, tag.children)
		return
	if name in _HEADINGS:
		heading = _text_of(tag)
		if heading:
			builder.heading(heading)
		return
	if name == "p":
		_add_paragraph(builder, tag)
		return
	if name in {"ul", "ol"}:
		items = _list_items(tag)
		if items:
			builder.bullets(items)
		return
	if name == "blockquote":
		text = _text_of(tag)
		if text:
			builder.paragraph(text)
		return
	if name == "a":
		_add_anchor(builder, tag)
		return
	if name in {"br", "hr"}:
		return
	_walk(builder, tag.children)


def _add_paragraph(builder: _Builder, tag: Tag) -> None:
	if _is_links_only(tag):
		for anchor in tag.find_all("a"):
			_add_anchor(builder, anchor)
		return
	text = _text_of(tag)
	if text:
		builder.paragraph(text)


def _add_anchor(builder: _Builder, tag: Tag) -> None:
	label = _text_of(tag)
	href = cstr(tag.get("href")).strip()
	if label and href:
		builder.link(label, href)


def _is_links_only(tag: Tag) -> bool:
	if not tag.find("a"):
		return False
	clone = BeautifulSoup(str(tag), "html.parser")
	for element in clone.find_all(["a", "br"]):
		element.decompose()
	return not clone.get_text(strip=True)


def _list_items(tag: Tag) -> list[str]:
	items = []
	for item in tag.find_all("li", recursive=False):
		text = _li_text(item)
		if text:
			items.append(text)
		for nested in item.find_all(["ul", "ol"], recursive=False):
			items.extend(_list_items(nested))
	return items


def _li_text(tag: Tag) -> str:
	parts = []
	for child in tag.children:
		if isinstance(child, Tag) and child.name in {"ul", "ol"}:
			continue
		text = _text_of(child)
		if text:
			parts.append(text)
	return " ".join(parts)


def _text_of(node) -> str:
	if node is None:
		return ""
	if isinstance(node, NavigableString):
		raw = cstr(node)
	else:
		raw = node.get_text(" ", strip=True)
	return unescape(raw.replace("\xa0", " ")).strip()
