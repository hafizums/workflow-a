from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np


class StoryboardDetectionError(ValueError):
    """Raised when storyboard panels cannot be detected from an image."""


@dataclass(frozen=True)
class PanelCandidate:
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    area: int

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2


def detect_storyboard_panels(
    image_path: str,
    output_dir: str,
    expected_count: int | None = None,
    padding_px: int = 8,
    debug: bool = False,
) -> dict[str, Any]:
    """Detect storyboard panels, save cropped panel images, and return metadata.

    Detection is based on OpenCV image processing only. It looks for panel-like
    rectangular regions with threshold/edge masks and falls back to a simple
    grid estimate when an expected panel count is provided but contour detection
    misses too many boxes.
    """

    source_path = Path(image_path)
    if expected_count is not None and expected_count <= 0:
        raise StoryboardDetectionError("expected_count must be a positive integer when provided.")
    if padding_px < 0:
        raise StoryboardDetectionError("padding_px must be zero or greater.")
    if not source_path.exists():
        raise StoryboardDetectionError(f"Could not read storyboard image: {image_path}")

    image = cv2.imread(str(source_path), cv2.IMREAD_COLOR)
    if image is None:
        raise StoryboardDetectionError(f"Could not read storyboard image: {image_path}")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    image_height, image_width = image.shape[:2]
    threshold_mask, edge_mask, contour_mask = _build_detection_masks(image)
    candidates = _find_panel_candidates(contour_mask, image_width, image_height)
    candidates = _nms(candidates, iou_threshold=0.28)

    if expected_count is not None:
        if len(candidates) > expected_count:
            candidates = _keep_best_candidates(candidates, expected_count)
        elif len(candidates) < expected_count:
            fallback = _fallback_grid_candidates(contour_mask, expected_count, image_width, image_height)
            candidates = _nms([*candidates, *fallback], iou_threshold=0.45)
            if len(candidates) > expected_count:
                candidates = _keep_best_candidates(candidates, expected_count)

    candidates = _sort_reading_order(candidates)
    if not candidates:
        raise StoryboardDetectionError("No storyboard panels found. Try a clearer sheet image or provide expected_count.")

    panels: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates, start=1):
        x1 = max(0, candidate.x1 - padding_px)
        y1 = max(0, candidate.y1 - padding_px)
        x2 = min(image_width, candidate.x2 + padding_px)
        y2 = min(image_height, candidate.y2 + padding_px)
        crop = image[y1:y2, x1:x2]
        crop_name = f"panel_{index:02d}.png"
        crop_path = out_dir / crop_name
        if crop.size == 0 or not cv2.imwrite(str(crop_path), crop):
            raise StoryboardDetectionError(f"Failed to write crop for panel {index}: {crop_path}")
        panels.append(
            {
                "index": index,
                "bbox_xyxy": [x1, y1, x2, y2],
                "bbox_norm": [
                    round(x1 / image_width, 4),
                    round(y1 / image_height, 4),
                    round(x2 / image_width, 4),
                    round(y2 / image_height, 4),
                ],
                "crop_path": crop_name,
                "confidence": round(candidate.confidence, 3),
            }
        )

    debug_image_path = ""
    if debug:
        debug_image_path = _write_debug_images(
            out_dir=out_dir,
            image=image,
            candidates=candidates,
            threshold_mask=threshold_mask,
            edge_mask=edge_mask,
            contour_mask=contour_mask,
        )

    return {
        "image_width": image_width,
        "image_height": image_height,
        "panel_count": len(panels),
        "panels": panels,
        "debug_image_path": debug_image_path,
    }


def _build_detection_masks(image: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    threshold_mask = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        7,
    )
    edge_mask = cv2.Canny(blurred, 40, 120)
    combined = cv2.bitwise_or(threshold_mask, edge_mask)

    height, width = gray.shape[:2]
    kernel_size = max(3, int(min(width, height) * 0.008))
    if kernel_size % 2 == 0:
        kernel_size += 1
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    dilate_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(3, kernel_size // 3), max(3, kernel_size // 3)))
    contour_mask = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, close_kernel, iterations=1)
    contour_mask = cv2.dilate(contour_mask, dilate_kernel, iterations=1)
    return threshold_mask, edge_mask, contour_mask


def _find_panel_candidates(mask: np.ndarray, image_width: int, image_height: int) -> list[PanelCandidate]:
    contours, _hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    page_area = image_width * image_height
    candidates: list[PanelCandidate] = []
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        x1, y1, x2, y2 = x, y, x + width, y + height
        area = width * height
        if not _candidate_size_ok(width, height, area, page_area, image_width, image_height):
            continue
        confidence = _candidate_confidence(contour, width, height, area, page_area)
        if confidence < 0.28:
            continue
        candidates.append(PanelCandidate(x1=x1, y1=y1, x2=x2, y2=y2, confidence=confidence, area=area))
    return candidates


def _candidate_size_ok(width: int, height: int, area: int, page_area: int, image_width: int, image_height: int) -> bool:
    if width <= 0 or height <= 0:
        return False
    area_ratio = area / page_area
    if area_ratio < 0.012 or area_ratio > 0.82:
        return False
    if width > image_width * 0.94 and height > image_height * 0.82:
        return False
    if width < image_width * 0.08 or height < image_height * 0.06:
        return False
    aspect = width / height
    return 0.28 <= aspect <= 4.2


def _candidate_confidence(contour: np.ndarray, width: int, height: int, area: int, page_area: int) -> float:
    contour_area = max(float(cv2.contourArea(contour)), 1.0)
    bbox_area = max(float(width * height), 1.0)
    rectangularity = min(contour_area / bbox_area, 1.0)
    extent_score = 1.0 - min(abs(0.08 - (area / page_area)) / 0.18, 0.55)
    aspect = width / max(height, 1)
    aspect_score = 1.0 if 0.45 <= aspect <= 2.6 else 0.68
    return max(0.0, min(0.98, (rectangularity * 0.55) + (extent_score * 0.25) + (aspect_score * 0.20)))


def _nms(candidates: list[PanelCandidate], iou_threshold: float) -> list[PanelCandidate]:
    kept: list[PanelCandidate] = []
    for candidate in sorted(candidates, key=lambda item: (item.confidence, item.area), reverse=True):
        if all(_iou(candidate, other) < iou_threshold for other in kept):
            kept.append(candidate)
    return kept


def _iou(a: PanelCandidate, b: PanelCandidate) -> float:
    x1 = max(a.x1, b.x1)
    y1 = max(a.y1, b.y1)
    x2 = min(a.x2, b.x2)
    y2 = min(a.y2, b.y2)
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    if intersection == 0:
        return 0.0
    union = a.area + b.area - intersection
    return intersection / union if union else 0.0


def _keep_best_candidates(candidates: list[PanelCandidate], count: int) -> list[PanelCandidate]:
    return sorted(candidates, key=lambda item: (item.confidence, item.area), reverse=True)[:count]


def _fallback_grid_candidates(mask: np.ndarray, expected_count: int, image_width: int, image_height: int) -> list[PanelCandidate]:
    rows, cols = _estimate_grid_shape(expected_count, image_width, image_height)
    bounds = _content_bounds(mask, image_width, image_height)
    x1, y1, x2, y2 = bounds
    total_width = max(1, x2 - x1)
    total_height = max(1, y2 - y1)
    gap_x = max(4, int(total_width * 0.018))
    gap_y = max(4, int(total_height * 0.018))
    candidates: list[PanelCandidate] = []
    for row in range(rows):
        for col in range(cols):
            if len(candidates) >= expected_count:
                break
            cell_x1 = x1 + int(col * total_width / cols) + gap_x
            cell_x2 = x1 + int((col + 1) * total_width / cols) - gap_x
            cell_y1 = y1 + int(row * total_height / rows) + gap_y
            cell_y2 = y1 + int((row + 1) * total_height / rows) - gap_y
            area = max(0, cell_x2 - cell_x1) * max(0, cell_y2 - cell_y1)
            candidates.append(
                PanelCandidate(
                    x1=max(0, cell_x1),
                    y1=max(0, cell_y1),
                    x2=min(image_width, cell_x2),
                    y2=min(image_height, cell_y2),
                    confidence=0.55,
                    area=area,
                )
            )
    return candidates


def _estimate_grid_shape(expected_count: int, image_width: int, image_height: int) -> tuple[int, int]:
    best_rows = 1
    best_cols = expected_count
    image_aspect = image_width / max(image_height, 1)
    best_score = float("inf")
    for rows in range(1, expected_count + 1):
        cols = int(np.ceil(expected_count / rows))
        grid_aspect = cols / rows
        score = abs(grid_aspect - image_aspect) + ((rows * cols) - expected_count) * 0.15
        if score < best_score:
            best_rows, best_cols, best_score = rows, cols, score
    return best_rows, best_cols


def _content_bounds(mask: np.ndarray, image_width: int, image_height: int) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask > 0)
    if xs.size == 0 or ys.size == 0:
        margin_x = int(image_width * 0.04)
        margin_y = int(image_height * 0.04)
        return margin_x, margin_y, image_width - margin_x, image_height - margin_y
    pad_x = int(image_width * 0.015)
    pad_y = int(image_height * 0.015)
    return (
        max(0, int(xs.min()) - pad_x),
        max(0, int(ys.min()) - pad_y),
        min(image_width, int(xs.max()) + pad_x),
        min(image_height, int(ys.max()) + pad_y),
    )


def _sort_reading_order(candidates: list[PanelCandidate]) -> list[PanelCandidate]:
    if not candidates:
        return []
    heights = sorted(candidate.height for candidate in candidates)
    median_height = heights[len(heights) // 2]
    row_tolerance = max(12, median_height * 0.45)
    rows: list[list[PanelCandidate]] = []
    for candidate in sorted(candidates, key=lambda item: item.center_y):
        for row in rows:
            row_center = sum(item.center_y for item in row) / len(row)
            if abs(candidate.center_y - row_center) <= row_tolerance:
                row.append(candidate)
                break
        else:
            rows.append([candidate])
    ordered: list[PanelCandidate] = []
    for row in sorted(rows, key=lambda items: sum(item.center_y for item in items) / len(items)):
        ordered.extend(sorted(row, key=lambda item: item.x1))
    return ordered


def _write_debug_images(
    *,
    out_dir: Path,
    image: np.ndarray,
    candidates: list[PanelCandidate],
    threshold_mask: np.ndarray,
    edge_mask: np.ndarray,
    contour_mask: np.ndarray,
) -> str:
    cv2.imwrite(str(out_dir / "threshold_mask.png"), threshold_mask)
    cv2.imwrite(str(out_dir / "edge_mask.png"), edge_mask)
    cv2.imwrite(str(out_dir / "contour_debug.png"), contour_mask)
    debug_image = image.copy()
    for index, candidate in enumerate(_sort_reading_order(candidates), start=1):
        cv2.rectangle(debug_image, (candidate.x1, candidate.y1), (candidate.x2, candidate.y2), (0, 180, 0), 3)
        cv2.putText(
            debug_image,
            str(index),
            (candidate.x1 + 8, candidate.y1 + 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )
    debug_name = "debug_detected_panels.png"
    cv2.imwrite(str(out_dir / debug_name), debug_image)
    return debug_name
