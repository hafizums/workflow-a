import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from app.services.storyboard_detector import StoryboardDetectionError, detect_storyboard_panels


class StoryboardDetectorTests(unittest.TestCase):
    def test_detects_synthetic_two_by_four_storyboard(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            image_path = temp_path / "storyboard.png"
            expected_boxes = make_storyboard_sheet(image_path, rows=2, cols=4)
            output_dir = temp_path / "out"

            result = detect_storyboard_panels(str(image_path), str(output_dir), expected_count=8, debug=True)

            self.assertEqual(result["image_width"], 1200)
            self.assertEqual(result["image_height"], 700)
            self.assertEqual(result["panel_count"], 8)
            self.assertEqual([panel["index"] for panel in result["panels"]], list(range(1, 9)))
            self.assertTrue((output_dir / result["debug_image_path"]).exists())
            self.assertTrue((output_dir / "threshold_mask.png").exists())
            self.assertPanelOrder(result["panels"])
            for panel in result["panels"]:
                self.assertTrue((output_dir / panel["crop_path"]).exists())
                self.assertGreater(panel["confidence"], 0.25)
            self.assertBoxesRoughlyMatch(result["panels"], expected_boxes)

    def test_detects_noisy_blurred_storyboard(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            image_path = temp_path / "noisy_storyboard.png"
            make_storyboard_sheet(image_path, rows=2, cols=4, noisy=True, blurred=True)
            output_dir = temp_path / "out"

            result = detect_storyboard_panels(str(image_path), str(output_dir), expected_count=8)

            self.assertEqual(result["panel_count"], 8)
            self.assertPanelOrder(result["panels"])
            for index in range(1, 9):
                self.assertTrue((output_dir / f"panel_{index:02d}.png").exists())

    def test_detects_expected_count_none_from_contours(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            image_path = temp_path / "storyboard_3x3.png"
            make_storyboard_sheet(image_path, rows=3, cols=3, width=900, height=1100)
            output_dir = temp_path / "out"

            result = detect_storyboard_panels(str(image_path), str(output_dir), expected_count=None)

            self.assertEqual(result["panel_count"], 9)
            self.assertPanelOrder(result["panels"])

    def test_invalid_image_fails_gracefully(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(StoryboardDetectionError, "Could not read storyboard image"):
                detect_storyboard_panels(str(Path(temp_dir) / "missing.png"), str(Path(temp_dir) / "out"))

    def assertPanelOrder(self, panels):
        top_row = panels[: len(panels) // 2] if len(panels) == 8 else panels[:3]
        bottom_row = panels[len(panels) // 2 :] if len(panels) == 8 else panels[3:6]
        self.assertEqual([panel["bbox_xyxy"][0] for panel in top_row], sorted(panel["bbox_xyxy"][0] for panel in top_row))
        if bottom_row:
            self.assertEqual([panel["bbox_xyxy"][0] for panel in bottom_row], sorted(panel["bbox_xyxy"][0] for panel in bottom_row))
            self.assertLess(top_row[0]["bbox_xyxy"][1], bottom_row[0]["bbox_xyxy"][1])

    def assertBoxesRoughlyMatch(self, panels, expected_boxes):
        for panel, expected in zip(panels, expected_boxes):
            detected = panel["bbox_xyxy"]
            for detected_value, expected_value in zip(detected, expected):
                self.assertLess(abs(detected_value - expected_value), 25)


def make_storyboard_sheet(
    path: Path,
    *,
    rows: int,
    cols: int,
    width: int = 1200,
    height: int = 700,
    noisy: bool = False,
    blurred: bool = False,
) -> list[list[int]]:
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    margin_x = int(width * 0.055)
    margin_y = int(height * 0.08)
    gutter_x = int(width * 0.028)
    gutter_y = int(height * 0.05)
    panel_width = int((width - (2 * margin_x) - ((cols - 1) * gutter_x)) / cols)
    panel_height = int((height - (2 * margin_y) - ((rows - 1) * gutter_y)) / rows)
    boxes: list[list[int]] = []

    for row in range(rows):
        for col in range(cols):
            x1 = margin_x + col * (panel_width + gutter_x)
            y1 = margin_y + row * (panel_height + gutter_y)
            x2 = x1 + panel_width
            y2 = y1 + panel_height
            boxes.append([x1, y1, x2, y2])
            cv2.rectangle(image, (x1, y1), (x2, y2), (18, 18, 18), 5)
            cv2.rectangle(image, (x1 + 10, y1 + 10), (x2 - 10, y2 - 10), (246, 246, 246), -1)
            cv2.line(image, (x1 + 28, y1 + 42), (x2 - 28, y2 - 32), (180, 180, 180), 2)
            cv2.putText(
                image,
                str(len(boxes)),
                (x1 + 18, y1 + 34),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (35, 35, 35),
                2,
                cv2.LINE_AA,
            )

    if noisy:
        noise = np.random.default_rng(42).normal(0, 8, image.shape).astype(np.int16)
        image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    if blurred:
        image = cv2.GaussianBlur(image, (5, 5), 0)

    self_ok = cv2.imwrite(str(path), image)
    if not self_ok:
        raise AssertionError(f"Failed to write synthetic storyboard: {path}")
    return boxes


if __name__ == "__main__":
    unittest.main()
