# Model Exclusions

Catalog models are not silently dropped.

Use:

```text
app/data/model_exclusions.json
```

Format:

```json
[
  {
    "model_id": "example/model",
    "excluded": true,
    "reason": "Requires unsupported private setup or unsupported required schema field."
  }
]
```

Excluded models are disabled for runtime use, but remain inspectable through:

```text
GET /api/model-catalog/excluded
GET /api/model-catalog?include_excluded=true
```

After editing exclusions, restart the FastAPI dev server so the repository cache reloads.

