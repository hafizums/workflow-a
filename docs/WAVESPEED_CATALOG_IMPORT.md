# WaveSpeed Catalog Import

The V11 catalog importer converts the uploaded WaveSpeed workbook into app-native JSON.

Workbook location:

```text
docs/reference/wavespeed_model_catalog_drilldown.xlsx
```

Run:

```bash
python scripts/import_wavespeed_catalog.py docs/reference/wavespeed_model_catalog_drilldown.xlsx
```

Generated files:

```text
app/data/wavespeed_catalog.normalized.json
app/data/model_exclusions.json
```

The importer reads:

- `Models_Full`
- `API_Schemas`
- `Schema_Fields`
- `Capability_Summary`
- `Cheapest_By_Capability`

It normalizes workbook field types into frontend/runtime field types such as `textarea`, `select`, `asset_url`, `asset_url_list`, `boolean`, `integer`, `number`, and `json`.

The importer does not call WaveSpeed and does not spend credits.

