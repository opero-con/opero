from __future__ import annotations

from frappe.model.document import Document
from frappe.utils import cstr

from opero.opero_site.utils import hero_carousel_entry, normalize_hero_image_focus


class Hero(Document):
	def to_site_frontmatter(self) -> dict:
		hero = {
			"eyebrow": cstr(self.hero_eyebrow).strip(),
			"title": cstr(self.hero_title).strip(),
			"description": cstr(self.hero_description).strip(),
		}
		frames = [row for row in (self.hero_images or []) if cstr(row.image).strip()]
		if not frames:
			return hero

		primary = frames[0]
		hero["image"] = cstr(primary.image)
		if cstr(primary.image_alt).strip():
			hero["imageAlt"] = cstr(primary.image_alt).strip()
		if cstr(primary.note).strip():
			hero["note"] = cstr(primary.note).strip()
		primary_focus = normalize_hero_image_focus(primary.image_focus)
		if primary_focus != "center":
			hero["imageFocus"] = primary_focus

		carousel = []
		for row in frames[1:]:
			entry = hero_carousel_entry(row.image, row.note, row.image_focus)
			if entry:
				carousel.append(entry)
		if carousel:
			hero["carousel"] = carousel
		return hero
