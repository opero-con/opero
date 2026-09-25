from __future__ import annotations

import io
from typing import NamedTuple

import frappe
from PIL import Image, ImageFilter, ImageStat

from opero.opero_site.markdown import parse_frontmatter

TARGET_ASPECT_RATIO = 1.6  # opero-frontend card tile: aspect-ratio 16 / 10
CONTAIN = "contain"
COVER = "cover"
_SALIENCY_MAX_DIMENSION = 400
_SCAN_STEPS = 20
_RATIO_TOLERANCE = 0.02
_MIN_KEPT_EDGE_SHARE = 0.85
_CENTER_PREFERENCE = 0.3  # tracks the team's hand-tuned crops; raw argmax jumps to the extremes


class CoverFraming(NamedTuple):
	fit: str
	position: str


def compute_cover_framing(image_bytes: bytes) -> CoverFraming:
	"""How the site should frame a cover in the card tile.

	Crops to the busiest region (`object-position`). A cover too wide to crop
	without losing much of its content, such as a slide, is shown whole instead.
	"""
	edges = _edge_map(image_bytes)
	width, height = edges.size
	image_ratio = width / height
	if abs(image_ratio - TARGET_ASPECT_RATIO) <= _RATIO_TOLERANCE:
		return CoverFraming(COVER, "center center")
	if image_ratio > TARGET_ASPECT_RATIO:
		offset, kept_share = _best_window(edges, width, round(height * TARGET_ASPECT_RATIO), horizontal=True)
		fit = COVER if kept_share >= _MIN_KEPT_EDGE_SHARE else CONTAIN
		return CoverFraming(fit, f"{offset}% center")
	offset, _ = _best_window(edges, height, round(width / TARGET_ASPECT_RATIO), horizontal=False)
	return CoverFraming(COVER, f"center {offset}%")


def _edge_map(image_bytes: bytes) -> Image.Image:
	image = Image.open(io.BytesIO(image_bytes)).convert("L")
	image.thumbnail((_SALIENCY_MAX_DIMENSION, _SALIENCY_MAX_DIMENSION))
	edges = image.filter(ImageFilter.FIND_EDGES)
	# Pillow leaves the outer 1px frame unfiltered, which would read as edges.
	return edges.crop((1, 1, edges.width - 1, edges.height - 1))


def _best_window(
	edges: Image.Image, full_length: int, window_length: int, *, horizontal: bool
) -> tuple[int, float]:
	"""Offset (percent) of the best window, and the share of all edges it keeps.

	Windows score by edge energy, discounted the further they sit from center.
	"""
	window_length = min(window_length, full_length)
	max_offset = full_length - window_length
	if max_offset <= 0:
		return 50, 1.0
	step = max(1, max_offset // _SCAN_STEPS)
	best_offset, best_score, best_energy = 0, -1.0, 0.0
	for offset in range(0, max_offset + 1, step):
		box = (
			(offset, 0, offset + window_length, edges.height)
			if horizontal
			else (0, offset, edges.width, offset + window_length)
		)
		energy = ImageStat.Stat(edges.crop(box)).sum[0]
		score = energy * (1 - _CENTER_PREFERENCE * abs(offset / max_offset - 0.5) * 2)
		if score > best_score:
			best_offset, best_score, best_energy = offset, score, energy
	total = ImageStat.Stat(edges).sum[0] or 1.0
	return round(best_offset / max_offset * 100), best_energy / total


def fill_missing_cover_framing(repo) -> None:
	"""Set framing for covers that live in the content repo as `/media/...`.

	Covers loaded from the website are never Desk files, so saving cannot read
	them. Framing already set on GitHub wins; otherwise it is computed.
	"""
	rows = frappe.get_all(
		"Publication",
		filters={"cover": ["like", "/media/%"], "cover_position": ["in", ("", None)]},
		fields=["name", "cover"],
	)
	paths = [f"content/publications/{row.name}.md" for row in rows]
	existing = repo.existing_files(paths, repo.base_branch) if paths else {}
	for row, path in zip(rows, paths, strict=True):
		framing = _framing_from_frontmatter(existing.get(path)) or _framing_from_image(repo, row.cover)
		if framing:
			frappe.db.set_value(
				"Publication",
				row.name,
				{"cover_fit": framing.fit, "cover_position": framing.position},
				update_modified=False,
			)


def _framing_from_frontmatter(text: str | None) -> CoverFraming | None:
	data = parse_frontmatter(text) if text else {}
	if "coverPosition" not in data and "coverFit" not in data:
		return None
	fit = CONTAIN if data.get("coverFit") == CONTAIN else COVER
	return CoverFraming(fit, str(data.get("coverPosition") or ""))


def _framing_from_image(repo, cover: str) -> CoverFraming | None:
	content = repo.get_blob_bytes(cover.lstrip("/"), repo.base_branch)
	if not content:
		return None
	try:
		return compute_cover_framing(content)
	except (OSError, ValueError):
		frappe.log_error(title="Cover framing")
		return None
