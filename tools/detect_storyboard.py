from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.storyboard_detector import StoryboardDetectionError, detect_storyboard_panels


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect and crop storyboard panels from a sheet image.")
    parser.add_argument("--input", required=True, help="Path to the storyboard sheet image.")
    parser.add_argument("--out", required=True, help="Directory where panel crops and debug files are written.")
    parser.add_argument("--expected", type=int, default=None, help="Optional expected number of panels.")
    parser.add_argument("--padding", type=int, default=8, help="Padding in pixels to include around each crop.")
    parser.add_argument("--debug", action="store_true", help="Write numbered debug image and intermediate masks.")
    args = parser.parse_args()

    try:
        result = detect_storyboard_panels(
            image_path=args.input,
            output_dir=args.out,
            expected_count=args.expected,
            padding_px=args.padding,
            debug=args.debug,
        )
    except StoryboardDetectionError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
