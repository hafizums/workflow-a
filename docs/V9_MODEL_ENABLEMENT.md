# V9 Model Enablement

V9 enabled a first batch of additional WaveSpeed model workflows. V11 now adds a catalog-driven runtime on top of those curated nodes, so many models that were previously planned are available as enabled `generic_wavespeed` catalog models. All examples use placeholder URLs and no secrets. Set `WAVESPEED_API_KEY` in the environment before live runs.

Localhost URLs are not reachable by WaveSpeed. Upload local files with `upload_to_wavespeed=true` or use public HTTPS URLs.

## Inspect Models

```bash
curl http://localhost:8000/api/models
```

For the full V11 catalog, use:

```bash
curl http://localhost:8000/api/model-catalog/summary
curl http://localhost:8000/api/model-catalog?capability=text_to_image
```

## Upload Assets

```bash
curl -X POST "http://localhost:8000/api/assets/upload?upload_to_wavespeed=true" \
  -F "file=@sample.mp3"
```

The returned asset can be used by ID inside saved projects, or by its `wavespeed_url`/`public_url` in direct run calls.

## Text To Video

```bash
curl -X POST http://localhost:8000/api/runs/node \
  -H "Content-Type: application/json" \
  -d '{
    "node_type": "text_to_video",
    "model_id": "wavespeed-ai/wan-2.2/t2v-480p-ultra-fast",
    "inputs": {
      "prompt": "A compact product camera move on a glass desk",
      "negative_prompt": "",
      "size": "832*480",
      "duration": 5,
      "seed": -1
    },
    "save_to_project": false
  }'
```

## Start-End Video

```bash
curl -X POST http://localhost:8000/api/runs/node \
  -H "Content-Type: application/json" \
  -d '{
    "node_type": "start_end_to_video",
    "model_id": "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast",
    "inputs": {
      "image": "https://example.com/start.png",
      "last_image": "https://example.com/end.png",
      "prompt": "Smooth motion from first frame to final frame",
      "duration": 5,
      "seed": -1
    },
    "save_to_project": false
  }'
```

## Speech To Text

```bash
curl -X POST http://localhost:8000/api/runs/node \
  -H "Content-Type: application/json" \
  -d '{
    "node_type": "speech_to_text",
    "model_id": "wavespeed-ai/openai-whisper",
    "inputs": {
      "audio": "https://example.com/speech.mp3",
      "language": "auto",
      "task": "transcribe",
      "enable_timestamps": false,
      "prompt": "",
      "enable_sync_mode": false
    },
    "save_to_project": false
  }'
```

Speech-to-text may return text without media URLs. The backend stores transcript text in `last_run.text_output` for saved node runs.

## Generate Voice

```bash
curl -X POST http://localhost:8000/api/runs/node \
  -H "Content-Type: application/json" \
  -d '{
    "node_type": "generate_voice",
    "model_id": "wavespeed-ai/qwen3-tts/voice-design",
    "inputs": {
      "text": "Welcome to the launch.",
      "voice_description": "Warm, confident narrator with a clean studio sound",
      "language": "English"
    },
    "save_to_project": false
  }'
```

## Lip Sync

```bash
curl -X POST http://localhost:8000/api/runs/node \
  -H "Content-Type: application/json" \
  -d '{
    "node_type": "lip_sync",
    "model_id": "wavespeed-ai/latentsync",
    "inputs": {
      "video": "https://example.com/talking-head.mp4",
      "audio": "https://example.com/speech.mp3"
    },
    "save_to_project": false
  }'
```

## Talking Avatar

```bash
curl -X POST http://localhost:8000/api/runs/node \
  -H "Content-Type: application/json" \
  -d '{
    "node_type": "talking_avatar",
    "model_id": "wavespeed-ai/infinitetalk",
    "inputs": {
      "image": "https://example.com/person.png",
      "audio": "https://example.com/speech.mp3",
      "prompt": "Natural expression",
      "resolution": "480p",
      "seed": -1
    },
    "save_to_project": false
  }'
```

`mask_image` is optional here. If supplied, it must be an uploaded or public image URL.

## Text To 3D

```bash
curl -X POST http://localhost:8000/api/runs/node \
  -H "Content-Type: application/json" \
  -d '{
    "node_type": "text_to_3d",
    "model_id": "wavespeed-ai/hunyuan-3d-v3.1/text-to-3d-rapid",
    "inputs": {
      "prompt": "A small ceramic vase with soft bevels"
    },
    "save_to_project": false
  }'
```

Returned `.glb`, `.gltf`, `.obj`, `.fbx`, `.stl`, `.usdz`, or `.zip` URLs are stored as `other` assets for V9.

## Remove Object / Inpaint

```bash
curl -X POST http://localhost:8000/api/runs/node \
  -H "Content-Type: application/json" \
  -d '{
    "node_type": "remove_object",
    "model_id": "wavespeed-ai/z-image/turbo-inpaint",
    "inputs": {
      "prompt": "Remove the logo and reconstruct the background",
      "image": "https://example.com/source.png",
      "mask_image": "https://example.com/mask.png",
      "size": "1024*1024"
    },
    "save_to_project": false
  }'
```

V9 does not include a mask editor. Upload or provide the mask image yourself.

## Reference To Image

```bash
curl -X POST http://localhost:8000/api/runs/node \
  -H "Content-Type: application/json" \
  -d '{
    "node_type": "reference_to_image",
    "model_id": "wavespeed-ai/z-image-turbo/image-to-image",
    "inputs": {
      "reference_image": "https://example.com/reference.png",
      "prompt": "Create a new product poster using this composition",
      "size": "1024*1024",
      "strength": 0.6,
      "seed": -1,
      "output_format": "jpeg"
    },
    "save_to_project": false
  }'
```

## V11 Catalog Policy

Normal add-node menus use `/api/models?enabled_only=true` and show enabled curated/catalog models. Catalog rows excluded from runtime are not shown as runnable add-node cards; inspect them through:

```text
GET /api/model-catalog/excluded
GET /api/model-catalog?include_excluded=true
```

Do not invent request parameters for a model that is not represented by verified registry or catalog schema metadata.

## Live Smoke Helper

After automated tests pass, live WaveSpeed dry-runs can be executed with:

```bash
python scripts/live_wavespeed_v9_smoke.py --confirm-spend-credits
```

The script refuses to run without `--confirm-spend-credits`. Cases that need media are skipped unless these environment variables are set. You may provide either public URLs or local paths; local paths are uploaded to WaveSpeed during the confirmed live run.

```bash
export V9_IMAGE_URL="https://example.com/source.png"
export V9_SECOND_IMAGE_URL="https://example.com/end.png"
export V9_MASK_IMAGE_URL="https://example.com/mask.png"
export V9_AUDIO_URL="https://example.com/speech.mp3"
export V9_VIDEO_URL="https://example.com/talking-head.mp4"

# Or local files:
export V9_IMAGE_PATH="./samples/source.png"
export V9_SECOND_IMAGE_PATH="./samples/end.png"
export V9_MASK_IMAGE_PATH="./samples/mask.png"
export V9_AUDIO_PATH="./samples/speech.mp3"
export V9_VIDEO_PATH="./samples/talking-head.mp4"
```

Run one case at a time with:

```bash
python scripts/live_wavespeed_v9_smoke.py --confirm-spend-credits --case speech_to_text
```
