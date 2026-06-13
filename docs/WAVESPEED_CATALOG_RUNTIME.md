# WaveSpeed Catalog Runtime

V11 keeps curated friendly nodes and adds catalog-scale generic execution.

Curated nodes still use their existing node types and tuned preparers, for example:

- `text_to_image`
- `image_to_image`
- `image_to_video`
- `text_to_speech`
- `talking_avatar`

Catalog-scale models use:

```json
{
  "node_type": "generic_wavespeed",
  "model_id": "actual/provider/model-id"
}
```

The runtime resolves models by exact `model_id` first. If a model is not one of the curated friendly models, it runs through:

- `app/services/model_input_resolver.py`
- `app/services/model_output_normalizer.py`

Direct generic run example:

```bash
curl -X POST http://localhost:8000/api/runs/node \
  -H "Content-Type: application/json" \
  -d '{
    "node_type": "generic_wavespeed",
    "model_id": "alibaba/happyhorse-1.0/text-to-video",
    "inputs": {
      "prompt": "A clean product reveal on a studio table",
      "duration": 5,
      "resolution": "720p"
    },
    "save_to_project": false
  }'
```

Asset fields accept project asset IDs, WaveSpeed URLs, public HTTPS URLs, and existing local file paths. Local files are uploaded through WaveSpeed before model execution. Localhost/private URLs are rejected because WaveSpeed cannot fetch them.

Text-only outputs are stored in `last_run.text_output`. JSON-only outputs are stored in `last_run.structured_output`.

