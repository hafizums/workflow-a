# V11 Catalog Scale-Out

V11 upgrades the app from a hand-enabled model batch to a catalog-driven WaveSpeed runtime.

Implemented pieces:

- Normalized workbook importer.
- Generated catalog JSON with 1009 models and 5226 schema fields.
- Catalog repository service.
- `/api/model-catalog` search/filter endpoints.
- Slash-safe model ID lookup endpoints.
- `/api/models` includes curated models, catalog models, and local utility tools.
- Exact model-ID resolution before node-type fallback.
- Generic `generic_wavespeed` node execution.
- Schema-driven input resolver.
- Generic output normalizer for URL, text, and JSON outputs.
- Catalog-aware model comparison and variants.
- Minimal vanilla frontend support for searchable catalog nodes and generic schemas.
- Cost metadata carries `base_price`, `pricing_basis_guess`, and `pricing_formula_raw`.

Useful checks:

```bash
python scripts/import_wavespeed_catalog.py docs/reference/wavespeed_model_catalog_drilldown.xlsx
python -m pytest
python -m uvicorn app.main:app --reload --port 8000
```

Endpoints:

```text
GET /api/model-catalog/summary
GET /api/model-catalog/capabilities
GET /api/model-catalog/capabilities/text_to_image
GET /api/model-catalog/models/wavespeed-ai/z-image/turbo
GET /api/model-catalog/models/alibaba/happyhorse-1.0/text-to-video
GET /api/model-catalog/models/akool/video-face-swap/schema
GET /api/model-catalog/excluded
GET /api/models?enabled_only=true
```

Live smoke tests should use a real `WAVESPEED_API_KEY` and small/cheap models first. Unit tests mock WaveSpeed calls and do not spend credits.

