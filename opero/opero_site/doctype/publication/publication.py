from __future__ import annotations

import os
import re
import shutil

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr, get_files_path, getdate
from frappe.utils.file_manager import is_safe_path

from opero.opero_site.body_html import body_sections_to_html, html_to_body_sections, normalize_body_html
from opero.opero_site.cover_focal_point import CONTAIN, compute_cover_framing
from opero.opero_site.media import desk_file_url, read_desk_file
from opero.opero_site.publish_status import LIVE, apply_publish_status, get_publish_status
from opero.opero_site.utils import (
	normalize_publication_type,
	optional_url,
	slugify,
)


class Publication(Document):
	def _validate_links(self):
		self.publication_type = normalize_publication_type(self.publication_type)
		for row in self.topics or []:
			title = cstr(row.topic).strip()
			if title:
				row.topic = title
				_ensure_publication_topic(title)
		super()._validate_links()

	def validate(self):
		apply_publish_status(self)
		# The site bumps `views` with a bare UPDATE, so a form opened before a
		# visit would write its stale copy back and reset the count.
		if not self.is_new():
			self.views = cint(frappe.db.get_value("Publication", self.name, "views"))
		self.title = cstr(self.title).strip()
		self.set_slug()
		self.file_url = optional_url(self.file_url, "File URL")
		self.page_url = optional_url(self.page_url, "Page URL")
		self.external_url = optional_url(self.external_url, "External URL")
		self.video_embed_url = optional_url(self.video_embed_url, "Embed URL")
		if self.video_embed_url and not cstr(self.video_title).strip():
			frappe.throw(_("Accessible title is required when an embed URL is set."))
		if self.published_on:
			self.year = getdate(self.published_on).year
		self.move_long_summary_to_body()
		self.body = normalize_body_html(self.body)
		self._set_cover_framing()

	def set_slug(self):
		"""Unique website slug; a blank one comes from the title, numbered when another publication has it."""
		typed = cstr(self.slug).strip()
		self.slug = slugify(typed or self.title)
		if not self.slug:
			frappe.throw(_("Slug must contain at least one letter or number."))
		if not typed:
			self.slug = self.get_free_slug(self.slug)
		elif self.is_slug_taken(self.slug):
			frappe.throw(_("Another publication already uses the slug {0}.").format(self.slug))
		self.validate_live_slug()

	def get_free_slug(self, base: str) -> str:
		slug, number = base, 1
		while self.is_slug_taken(slug):
			number += 1
			slug = f"{base}-{number}"
		return slug

	def is_slug_taken(self, slug: str) -> bool:
		return bool(frappe.db.exists("Publication", {"slug": slug, "name": ["!=", self.name or ""]}))

	def validate_live_slug(self):
		"""A live publication keeps its URL; unpublish and deploy it before changing the slug."""
		previous = None if self.is_new() else self.get_doc_before_save()
		if previous and previous.slug != self.slug and get_publish_status(previous) in LIVE:
			frappe.throw(_("{0} is on the website, so its slug can't change.").format(self.title))

	def move_long_summary_to_body(self):
		"""Move a multi-paragraph summary into an empty body, keeping its first paragraph."""
		if frappe.flags.get("opero_site_syncing") or html_to_body_sections(self.body):
			return
		paragraphs = [part.strip() for part in re.split(r"\n\s*\n", cstr(self.summary)) if part.strip()]
		if len(paragraphs) < 2:
			return
		self.body = body_sections_to_html([{"paragraphs": paragraphs}])
		self.summary = paragraphs[0]
		frappe.msgprint(
			_(
				"The summary had several paragraphs, so they now form the body. The first paragraph stays as the summary."
			),
			alert=True,
		)

	def _set_cover_framing(self):
		if frappe.flags.get("opero_site_syncing") or not self.has_value_changed("cover"):
			return
		self.cover_fit = self.cover_position = ""
		file_url = desk_file_url(self.cover) if self.cover else None
		if not file_url:
			return
		try:
			framing = compute_cover_framing(read_desk_file(file_url))
		except (OSError, ValueError):
			frappe.log_error(title="Cover framing")
			return
		self.cover_fit, self.cover_position = framing

	def to_site_frontmatter(self) -> dict:
		payload = {
			"slug": self.slug,
			"title": cstr(self.title).strip(),
			"publishedAt": getdate(self.published_on).isoformat() if self.published_on else "",
			"type": cstr(self.publication_type).strip(),
			"summary": cstr(self.summary).strip(),
			"topics": [cstr(row.topic).strip() for row in (self.topics or []) if row.topic],
			"featured": bool(cint(self.featured)),
		}
		if self.year:
			payload["year"] = cint(self.year)
		if self.service_area:
			payload["serviceArea"] = cstr(self.service_area).strip()
		if self.cover:
			payload["cover"] = cstr(self.cover)
		if self.cover_alt:
			payload["coverAlt"] = cstr(self.cover_alt).strip()
		if self.cover_position:
			payload["coverPosition"] = cstr(self.cover_position)
		if self.cover_fit == CONTAIN:
			payload["coverFit"] = CONTAIN
		if self.file_url:
			payload["fileUrl"] = self.file_url
		if self.page_url:
			payload["pageUrl"] = self.page_url
		if self.external_url:
			payload["externalUrl"] = self.external_url
		if self.video_embed_url:
			payload["video"] = {
				"embedUrl": self.video_embed_url,
				"title": cstr(self.video_title).strip(),
			}
			if self.video_caption:
				payload["video"]["caption"] = cstr(self.video_caption).strip()
		body = html_to_body_sections(self.body)
		if body:
			payload["body"] = body
		return payload


_PDF_NAME_LIMIT = 140


@frappe.whitelist()
def rename_publication_pdf(name: str, filename: str) -> str:
	"""Rename the PDF already stored on this publication. Returns the new file URL."""
	doc = frappe.get_doc("Publication", name)
	doc.check_permission("write")
	new_url = _rename_stored_pdf(doc, filename)
	doc.save()
	return new_url


def _rename_stored_pdf(doc, filename: str) -> str:
	stored = cstr(doc.file_url).strip()
	old_url = desk_file_url(stored)
	if "://" in stored or not old_url or not stored.startswith(("/files/", "/private/files/")):
		frappe.throw(
			_("This PDF is a link, so rename it where the file is hosted."),
			title=_("PDF is a link"),
		)
	new_name = _publication_pdf_filename(filename)
	current_name = os.path.basename(old_url)
	if new_name == current_name:
		frappe.throw(
			_("This PDF is already named {0}.").format(current_name),
			title=_("File name unchanged"),
		)
	is_private = old_url.startswith("/private/files/")
	source = get_files_path(current_name, is_private=1 if is_private else 0)
	target = get_files_path(new_name, is_private=1 if is_private else 0)
	if (
		os.path.dirname(source) != os.path.dirname(target)
		or not is_safe_path(source)
		or not is_safe_path(target)
	):
		frappe.throw(
			_("This file name includes a path or one of these characters: / \\ % ? #."),
			title=_("File name not allowed"),
		)
	if not os.path.isfile(source):
		frappe.throw(_("This PDF is not on the site."), title=_("PDF not found"))
	new_url = f"{'/private/files/' if is_private else '/files/'}{new_name}"
	if os.path.exists(target) or frappe.db.exists("File", {"file_url": new_url}):
		frappe.throw(
			_("A file named {0} is already on the site. Choose a different name.").format(new_name),
			title=_("File name already used"),
		)
	_claim_pdf_rows(doc, {stored, old_url})

	def restore_publication_pdf() -> None:
		if os.path.exists(target) and not os.path.exists(source):
			shutil.move(target, source)

	frappe.db.after_rollback.add(restore_publication_pdf)
	shutil.move(source, target)
	for file_id in frappe.get_all(
		"File", filters={"file_url": ["in", list({stored, old_url})]}, pluck="name"
	):
		frappe.db.set_value("File", file_id, {"file_name": new_name, "file_url": new_url})
	doc.file_url = new_url
	return new_url


def _claim_pdf_rows(doc, urls: set[str]) -> None:
	rows = frappe.get_all(
		"File",
		filters={"file_url": ["in", list(urls)]},
		fields=["name", "attached_to_doctype", "attached_to_name", "attached_to_field"],
	)
	for row in rows:
		doctype = cstr(row.attached_to_doctype)
		attached_name = cstr(row.attached_to_name)
		if not doctype and not attached_name:
			continue
		field = cstr(row.attached_to_field)
		if doctype == doc.doctype and attached_name == doc.name:
			if field and field != "file_url":
				label = field
				meta_field = frappe.get_meta(doc.doctype).get_field(field)
				if meta_field and meta_field.label:
					label = _(meta_field.label)
				frappe.throw(
					_("This PDF is also the {0} on this publication.").format(label),
					title=_("PDF is used elsewhere"),
				)
			continue
		frappe.throw(
			_("This PDF is also attached to {0} {1}, so it can't be renamed here.").format(
				doctype, attached_name
			),
			title=_("PDF is used elsewhere"),
		)


def _publication_pdf_filename(value: str) -> str:
	name = cstr(value).strip().replace("\u00a0", " ")
	if not name:
		frappe.throw(_("Enter a PDF file name."), title=_("File name required"))
	base, ext = os.path.splitext(name)
	base = base.strip()
	if ext.lower() == ".pdf" or not ext:
		name = f"{base}.pdf"
	else:
		frappe.throw(_("The file name has to end in .pdf."), title=_("PDF file required"))
	if re.search(r"[/\\%?#\x00-\x1f]", name):
		frappe.throw(
			_("This file name includes a path or one of these characters: / \\ % ? #."),
			title=_("File name not allowed"),
		)
	if not base or base in {".", ".."} or name.startswith("."):
		frappe.throw(_("Enter a PDF file name."), title=_("File name required"))
	if len(name) > _PDF_NAME_LIMIT:
		frappe.throw(
			_("This file name is {0} characters. Use {1} or fewer.").format(len(name), _PDF_NAME_LIMIT),
			title=_("File name too long"),
		)
	return name


def _ensure_publication_topic(title: str) -> None:
	if frappe.db.exists("Publication Topic", title):
		return
	frappe.get_doc({"doctype": "Publication Topic", "title": title}).insert(
		ignore_permissions=True,
		ignore_if_duplicate=True,
	)
