from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.catalog_importer import import_catalog


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the WaveSpeed workbook into normalized app catalog JSON.")
    parser.add_argument("workbook", type=Path, help="Path to wavespeed_model_catalog_drilldown.xlsx")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("app/data/wavespeed_catalog.normalized.json"),
        help="Normalized JSON output path.",
    )
    parser.add_argument(
        "--exclusions",
        type=Path,
        default=Path("app/data/model_exclusions.json"),
        help="Model exclusions JSON path.",
    )
    args = parser.parse_args()
    counts = import_catalog(args.workbook, args.output, args.exclusions)
    print(
        "Imported {models} models, {schema_fields} schema fields, "
        "{capabilities} capabilities, and {cheapest_by_capability} cheapest rows.".format(**counts)
    )
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
