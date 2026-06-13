from pathlib import Path

from app.services.catalog_importer import import_catalog


def test_importer_reads_workbook_counts(tmp_path):
    output = tmp_path / "catalog.json"
    exclusions = tmp_path / "exclusions.json"
    counts = import_catalog(
        Path("docs/reference/wavespeed_model_catalog_drilldown.xlsx"),
        output,
        exclusions,
    )
    assert counts["models"] >= 900
    assert counts["schema_fields"] >= 5000
    assert output.exists()
