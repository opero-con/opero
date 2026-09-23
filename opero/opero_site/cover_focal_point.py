from __future__ import annotations

import io

from PIL import Image, ImageFilter, ImageStat

TARGET_ASPECT_RATIO = 1.6  # opero-site card tile: aspect-ratio 16 / 10
_SALIENCY_MAX_DIMENSION = 400
_SCAN_STEPS = 20
_RATIO_TOLERANCE = 0.02


def compute_cover_focal_point(image_bytes: bytes) -> str:
	"""CSS `object-position` that keeps the busiest region of the cover
	on-screen when the site crops it to the card's aspect ratio."""
	edges = _edge_map(image_bytes)
	width, height = edges.size
	image_ratio = width / height
	if abs(image_ratio - TARGET_ASPECT_RATIO) <= _RATIO_TOLERANCE:
		return "center center"
	if image_ratio > TARGET_ASPECT_RATIO:
		offset = _best_offset(edges, width, round(height * TARGET_ASPECT_RATIO), horizontal=True)
		return f"{offset}% center"
	offset = _best_offset(edges, height, round(width / TARGET_ASPECT_RATIO), horizontal=False)
	return f"center {offset}%"


def _edge_map(image_bytes: bytes) -> Image.Image:
	image = Image.open(io.BytesIO(image_bytes)).convert("L")
	image.thumbnail((_SALIENCY_MAX_DIMENSION, _SALIENCY_MAX_DIMENSION))
	return image.filter(ImageFilter.FIND_EDGES)


def _best_offset(edges: Image.Image, full_length: int, window_length: int, *, horizontal: bool) -> int:
	window_length = min(window_length, full_length)
	max_offset = full_length - window_length
	if max_offset <= 0:
		return 50
	step = max(1, max_offset // _SCAN_STEPS)
	best_offset, best_score = 0, -1.0
	for offset in range(0, max_offset + 1, step):
		box = (
			(offset, 0, offset + window_length, edges.height)
			if horizontal
			else (0, offset, edges.width, offset + window_length)
		)
		score = ImageStat.Stat(edges.crop(box)).sum[0]
		if score > best_score:
			best_offset, best_score = offset, score
	return round(best_offset / max_offset * 100)
