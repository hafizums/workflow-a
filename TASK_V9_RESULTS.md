# TASK V9 Results

## Status

V9 model enablement is implemented and live dry-run verified.

## Live WaveSpeed Dry-Run Results

Live calls were run with explicit `--confirm-spend-credits` approval on the local machine. Temporary local media files were created under the OS temp directory and uploaded to WaveSpeed where needed. No API keys or local media files are committed.

Successful priority batch:

- `text_to_video`: `wavespeed-ai/wan-2.2/t2v-480p-ultra-fast`
- `start_end_to_video`: `wavespeed-ai/wan-2.2/i2v-480p-ultra-fast`
- `speech_to_text`: `wavespeed-ai/openai-whisper`
- `generate_voice`: `wavespeed-ai/qwen3-tts/voice-design`
- `lip_sync`: `wavespeed-ai/latentsync`
- `talking_avatar`: `wavespeed-ai/infinitetalk`
- `text_to_3d`: `wavespeed-ai/hunyuan-3d-v3.1/text-to-3d-rapid`
- `remove_object`: `wavespeed-ai/z-image/turbo-inpaint`
- `reference_to_image`: `wavespeed-ai/z-image-turbo/image-to-image`

Notes:

- An initial lip-sync attempt failed because the sample MP4 had no detectable face. Retrying with a face-based talking-avatar output succeeded.
- Speech-to-text returned text-only output without media URLs, as expected.
- Text-to-3D returned a `.glb` URL and is stored as an `other` asset.

## Validation Commands

```powershell
python -m pytest -q
python -m compileall app
node --check web/app.js
python scripts\live_wavespeed_v9_smoke.py --confirm-spend-credits --case lip_sync
```

## Remaining Disabled Nodes

These remain intentionally disabled with specific reasons in the catalog:

- `text_to_audio`
- `reference_to_video`
- `video_extend`
- `video_effect`
- `portrait_transfer`
- `image_to_3d`
