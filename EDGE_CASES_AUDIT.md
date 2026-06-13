# Edge Cases Audit - WaveSpeed Canvas MVP

## Summary

* Total edge cases found: 52
* P0 count: 3
* P1 count: 25
* P2 count: 21
* P3 count: 3
* Already covered by tests count at audit time: 14
* Batch closure status: 52/52 edge cases are now either fixed with direct coverage, covered by existing tests, or documented as intentional MVP behavior.
* Remaining unresolved MVP edge cases from this audit: 0

The project has strong coverage for core MVP paths: settings validation, import/export basics, graph cycle/missing-node errors, prompt-source rules, asset resolution basics, generic catalog execution, run manager lifecycle, templates, recipes, artifact lineage, branching, variants, comparisons, and Playwright smoke flows. The largest remaining edge-case risks are around local path handling, concurrent project mutation, utility-node workflow semantics, route-level upload/import failure behavior, and clone/apply ID collisions.

## Batch Completion Status

This section records the implementation status after the edge-case fix batches. The matrix below remains the original discovery record, so some "Current observed behavior" and "Missing test" cells describe the pre-fix state.

### Batch 1 - P0/P1 Functional Fixes

Status: complete and validated.

Covered IDs:

* EC-001, EC-002: corrupt project list/load handling.
* EC-003, EC-035: atomic project writes and overlapping job protection.
* EC-004, EC-005, EC-006: local path, upload traversal, and private URL safety.
* EC-009, EC-012, EC-013, EC-015: graph-sourced text inputs, duplicate-edge warning/deduping, incompatible media planning, and stale local output checks.
* EC-029, EC-031: runnable local utility planning/job execution and stitch order validation.
* EC-042, EC-044, EC-045, EC-047, EC-048: recipe edge remapping, lineage cycle guard, video branch compatibility, variant clone targeting, and run-snapshot clone ID uniqueness.

Primary evidence:

* `tests/test_edge_case_batch1.py`
* `tests/test_asset_resolution.py`
* `tests/test_v6.py`
* `tests/test_v10_utility_nodes.py`
* `tests/test_v10_branching.py`
* `tests/test_v10_variants.py`

### Batch 2 - P2 Functional Polish And Regression Coverage

Status: complete and validated.

Covered IDs:

* EC-016, EC-017, EC-018, EC-019: unsupported upload behavior, MIME/suffix mismatch behavior, duplicate filename visibility, and cloud-upload cleanup on failure.
* EC-020, EC-021, EC-022: missing API key, provider exception redaction/wrapping, and malformed provider output saved-node error state.
* EC-024, EC-026, EC-028: denylisted model route behavior, direct-run save semantics, and generic catalog list min/max plus typed-asset rejection.
* EC-030, EC-032: direct stitch input count error and local utility output cleanup on failure.
* EC-039, EC-040, EC-043, EC-046, EC-049, EC-050, EC-051, EC-052: USD backend cost regression, import JSON/size errors, unknown template/recipe routes, artifact rating bounds, frontend error messages, stale project delete smoke path, unknown preview fallback, and denylisted/excluded route protections.

Primary evidence:

* `tests/test_edge_case_batch2.py`
* `frontend/tests/ui-smoke.spec.js`
* Existing route/service coverage in `tests/test_v3.py`, `tests/test_v4.py`, `tests/test_v5.py`, and `tests/test_v7.py`

### Batch 3 - P3 And Documentation Closure

Status: complete.

Covered IDs:

* EC-018: duplicate original filenames are intentionally allowed and displayed with asset IDs.
* EC-037: in-memory jobs disappear across `LocalRunManager` instances; terminal run history remains persisted by existing run-manager behavior.
* EC-051: unknown output URL types render safe fallback links and output actions.

Primary evidence:

* `tests/test_edge_case_batch2.py`
* `frontend/tests/ui-smoke.spec.js`

## Edge Case Matrix

| ID | Area | Related requirement ID if known | Severity | Scenario | Reproduction steps | Expected behavior | Current observed behavior from code | Existing test coverage | Missing test to add | Suggested fix location | Risk if ignored |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EC-001 | Project CRUD / local JSON persistence | FR-002, FR-003 | P1 | One malformed project JSON breaks project listing. | Put invalid JSON in `data/projects/project_badbadbadbad.json`, then call `GET /api/projects`. | Bad project file is skipped or reported without blocking all projects. | `app/services/project_store.py:list_projects` calls `read_json` and `Project.model_validate` without per-file error handling. | Missing. | API test for corrupt project file during list. | `app/services/project_store.py`, `app/infrastructure/repositories/json_project_repository.py`. | User cannot load any project from UI if one JSON file is corrupt. |
| EC-002 | Project CRUD / backward compatibility | FR-003, FR-026 | P1 | Loading a syntactically valid but schema-invalid project returns generic 500/422 behavior. | Save a project JSON with invalid enum/status, then `GET /api/projects/{id}`. | API returns clear storage/schema error for that project. | `Project.model_validate` exceptions are not wrapped in `ProjectStoreError`. Router only maps `ProjectStoreError`. | Weak: old project without settings is covered, invalid stored schema is not. | API test for invalid persisted enum or missing required fields. | `app/services/project_store.py`; router project error mapping. | A single stale/corrupt project can produce poor user-facing errors. |
| EC-003 | Project save consistency | FR-002, FR-003, FR-013 | P1 | Concurrent saves overwrite each other. | Queue a job that saves run output while frontend saves project metadata. | Latest project includes both graph edits and run output, or conflict is explicit. | `app/core/storage.py:write_json` writes full JSON without lock/atomic rename; `run_manager`, routes, and frontend saves can race. | Missing. | Unit/integration test with two concurrent saves to same project. | `app/infrastructure/repositories/project_transaction.py`, `app/services/project_store.py`. | Lost node outputs, stale project metadata, or missing run history. |
| EC-004 | Security / asset resolution | FR-009, FR-011, FR-026 | P0 | Direct model inputs can upload arbitrary existing server-local file paths to WaveSpeed. | Call `/api/runs/node` with `save_to_project=false`, an image/video/audio input set to `C:\...` or `/...` that exists. | API rejects arbitrary local paths unless they are known uploaded project assets. | `app/services/node_runner.py:resolve_asset_input` and `app/services/model_input_resolver.py:resolve_asset_value` upload any `Path(asset_ref).exists()`. | Missing. | Unit and API tests asserting raw local paths are rejected outside upload dir. | `node_runner.py`, `model_input_resolver.py`. | Local file disclosure to external provider. |
| EC-005 | Security / local utilities | FR-023, FR-026 | P0 | `/uploads/../...` style video references may resolve outside upload directory. | Run `video_last_frame` or `stitch_video` with `video` equal to `/uploads/../../somefile.mp4`. | Utility confines upload URL references to configured upload directory. | `app/services/local_utility_runner.py:local_upload_path` appends suffix after `/uploads/` without resolving and checking containment. | Missing. | Unit test for traversal-looking upload URL. | `app/services/local_utility_runner.py`. | Reads unintended local files if path exists and ffmpeg/imageio can open it. |
| EC-006 | Security / private URL filtering | FR-009, FR-011, FR-026 | P0 | Private/internal URLs outside the current allowlist are sent to WaveSpeed or downloaded locally. | Use `http://172.20.0.1/file.mp4`, `http://169.254.169.254/...`, or IPv6 private URL as model/local utility input. | All private, link-local, loopback, and local network URLs are rejected for remote model fetches. | `model_input_resolver.is_private_url` covers localhost, 127, ::1, 192.168, 10, and only `172.16.*`; `node_runner.is_local_url` misses most private ranges; local utility downloads any HTTP video URL. | Weak: localhost and 192/10 style rejection is partly covered. | Unit tests for full RFC1918 range, link-local, IPv6 loopback/private. | `model_input_resolver.py`, `node_runner.py`, `local_utility_runner.py`. | SSRF-style internal URL exposure to local downloader or external model service. |
| EC-007 | Prompt-source rules | FR-008, FR-026 | P1 | Required prompt missing on saved model node. | Create Text to Image node without Prompt Card edge and plan/run. | Clear `prompt_card_required` error. | `workflow_resolver.validate_prompt_card_inputs` enforces prompt/text for known model types. | Covered: `tests/test_v10_utility_nodes.py`, `tests/test_v4.py`. | None, unless adding API-level saved-node run assertion. | Already covered. | Low current risk. |
| EC-008 | Prompt-source rules | FR-008 | P1 | Prompt source exists but has not produced text/output yet. | Connect LLM text node to image prompt before LLM runs, then plan/run image. | Clear “source must run first” / missing upstream output error. | `resolve_inputs_for_node` emits `missing_upstream_output` when source output cannot resolve. | Covered: `test_unrun_llm_prompt_source_must_run_first`. | Add API test for `/api/runs/node` saved downstream node. | `workflow_resolver.py`, `RunNodeUseCase`. | Users may not know upstream node must run first if UI path not tested. |
| EC-009 | Prompt-source rules | FR-006, FR-008 | P2 | `negative_prompt` remains manually settable on model nodes. | Put `negative_prompt` directly in a saved model node and run with a valid prompt edge. | Product decision needed: either allow optional freeform negative prompt or require source node. | `prompt_card_only_inputs_for_node` only enforces `prompt` and `text`; frontend has handles for `negative_prompt` but backend does not require source. | Missing. | Policy test documenting allowed or rejected direct `negative_prompt`. | `workflow_resolver.py`, frontend `NodeField` behavior. | Inconsistent with “all text-like inputs come from source cards” expectation. |
| EC-010 | Canvas edges / graph planning | FR-007, FR-012 | P1 | Self-loop or cycle. | Create edge from node to itself or cycle A->B->A and plan. | Plan rejects with cycle error. | `workflow_resolver.find_cycle` catches cycles after `build_graph`. | Covered: `tests/test_v6.py`. | None. | Already covered. | Low current risk. |
| EC-011 | Canvas edges / graph planning | FR-007, FR-012 | P1 | Edge references missing source or target node. | Import/save project with edge pointing to missing node and plan/import. | Clear error. | `build_graph` emits `invalid_edge_source`/`invalid_edge_target`; import validates edges. | Covered: `tests/test_v5.py`, `tests/test_v6.py`. | None. | Already covered. | Low current risk. |
| EC-012 | Canvas edges / graph planning | FR-007 | P2 | Exact duplicate edge is accepted silently. | Add same edge twice and plan. | Requirement says duplicate should be blocked or reported. | `build_graph` appends both edges; tests only assert duplicates do not crash. | Weak: `test_duplicate_edges_do_not_crash_planning` does not require warning/block. | Test expecting duplicate warning or frontend prevention. | `workflow_resolver.py`, frontend `onConnect`/quick connect. | Duplicated list inputs, confusing graph state. |
| EC-013 | Canvas edges / graph planning | FR-007, FR-012 | P1 | Incompatible media type is not reported at planning time for many paths. | Connect image output to audio input, or video output to image input, then plan. | Plan reports incompatible media before running. | `resolve_inputs_for_node` only passes values; kind enforcement happens later in `node_runner`/`model_input_resolver`. | Weak: branch incompatibility and some resolver kind checks are covered, broad edge planning is not. | Workflow plan tests for mismatched image/video/audio handles. | `workflow_resolver.py`, `tool_compatibility.py`, frontend connection validation. | Users see late run failures after graph appears valid. |
| EC-014 | Canvas edges / reload | FR-003, FR-007 | P2 | Old edge alias fields reload. | Save/import edge with `source`, `target`, `sourceNodeId`, etc. | Normalizes into current source/target IDs. | `normalize_edge` supports aliases. | Covered: `tests/test_v6.py`. | None. | Already covered. | Low current risk. |
| EC-015 | Workflow resolver / outputs | FR-012, FR-026 | P1 | Stale output URL from source node points to deleted asset/file. | Delete local uploaded/generated file but leave `node.output_urls` or `output_asset_ids`, then plan/run downstream. | Resolver should detect missing project asset/local file when input is local-only. | `resolve_source_output` returns first `output_urls[0]` without checking whether `/uploads/...` still exists. Later model input resolution may reject localhost/public URL or upload missing local path. | Weak: missing upstream output covered only when no output exists. | Test for stale `/uploads` URL and deleted local file. | `workflow_resolver.py`, `node_runner.py`. | Graph says ready but run fails late or sends unusable local URL. |
| EC-016 | Asset upload | FR-009, FR-026 | P2 | Unsupported file type is accepted as `AssetKind.other`. | Upload `.exe`, `.txt`, or unknown binary. | Product decision: reject unsupported uploads or mark as other with clear UI limitations. | `assets.py:infer_asset_kind` returns `other`; route stores it. | Missing. | API test for unknown type behavior. | `app/routers/assets.py`; requirements decision. | Users can select assets that no model can use, causing later confusion. |
| EC-017 | Asset upload | FR-009 | P2 | MIME type and suffix disagree. | Upload `image.png` with `video/mp4`, or `clip.mp4` with `image/png`. | Kind detection should be deterministic and tested. | `infer_asset_kind` trusts content type first but also suffix; no content sniffing. | Weak: suffix detection covered in resolver, not upload route mismatch. | API test for mismatched MIME/suffix. | `app/routers/assets.py`. | Wrong asset kind can block valid runs or allow wrong media into nodes. |
| EC-018 | Asset upload | FR-009 | P3 | Duplicate original filenames appear identical in UI. | Upload two files named `image.png`. | Stored names remain unique and UI should distinguish assets. | Stored filename is UUID, but `Asset.filename` remains original; UI lists original plus ID. | Missing. | Frontend smoke for duplicate filename display/select. | `frontend/src/main.jsx`; maybe asset label formatting. | User may choose wrong asset. |
| EC-019 | Asset upload / WaveSpeed upload | FR-009, FR-011 | P2 | WaveSpeed upload failure leaves local upload file stored but no project asset. | Upload with `upload_to_wavespeed=true` and adapter failure. | Either remove local file or return partial asset intentionally. | `assets.py` writes local file first, then raises 400 on WaveSpeed failure without cleanup. | Missing. | API test with mocked adapter failure and file cleanup assertion. | `app/routers/assets.py`. | Orphan files accumulate; user sees failed upload but disk keeps file. |
| EC-020 | WaveSpeed adapter | FR-011, FR-026 | P1 | Missing API key error. | Run model without `WAVESPEED_API_KEY`. | Clear API error, no secret exposure. | `WaveSpeedAdapter.require_api_key` raises clear `RuntimeError`; route maps to 400 in run paths. | Missing direct test. | API/unit test for missing key through `/api/runs/node` and upload. | `wavespeed_adapter.py`, run/upload routes. | Confusing first-run setup failures. |
| EC-021 | WaveSpeed adapter | FR-011, FR-026 | P2 | Invalid API key, network failure, or timeout. | Mock SDK/httpx failure or timeout. | Backend returns provider detail without generic masking, no secret. | Adapter wraps SDK errors as `WaveSpeed run failed...`; LLM pathway includes response text. | Missing. | Unit tests for SDK exception, HTTPStatusError, timeout. | `app/services/wavespeed_adapter.py`. | Hard-to-debug provider errors in UI. |
| EC-022 | WaveSpeed adapter / output normalization | FR-010, FR-015 | P1 | Malformed provider response with no URL/text/structured output. | Mock `run_model` returning `{}` or non-dict. | Clear node error and saved failure state. | Adapter rejects non-dict; `node_runner.run_wavespeed_node` rejects empty normalized output. | Covered: preparer/output tests cover structured/text paths; empty output path is partially covered. | Add API test verifying saved node status becomes error. | `node_runner.py`, `RunNodeUseCase`. | Node may remain running/error handling regression. |
| EC-023 | WaveSpeed boundary | FR-011 | P1 | External AI client used outside adapter. | Search app code for non-adapter clients. | No direct external AI clients outside adapter. | `test_v10_wavespeed_only_guard` enforces client import guard. | Covered. | None. | Already covered. | Low current risk. |
| EC-024 | Single-node runs | FR-010, FR-022, FR-026 | P1 | Unknown, disabled, or excluded model. | Run with unknown model ID, disabled model, or excluded catalog row. | Clear 400; saved node marked error when applicable. | `registry.resolve_model_for_node` and `node_runner.current_denylist` guard execution. | Covered: `tests/test_v3.py`, registry/catalog tests, generic runner tests. | Add saved-node status persistence assertion for excluded catalog model. | `registry.py`, `node_runner.py`, `RunNodeUseCase`. | Accidental paid/unsupported external calls. |
| EC-025 | Single-node runs | FR-010, FR-022 | P1 | Missing required inputs or invalid schema values. | Run without required prompt/image/audio or invalid select/integer/number. | Clear field-specific error. | Curated preparers and `prepare_model_inputs` validate required fields and types. | Covered: `tests/test_node_runner_preparers.py`, `tests/test_generic_wavespeed_runner.py`. | Add API-level field error test for generic catalog model. | `node_runner.py`, `model_input_resolver.py`. | Provider calls with bad payloads. |
| EC-026 | Single-node runs | FR-010 | P2 | `save_to_project=false` skips project input resolution and status persistence. | Call `/api/runs/node` with `project_id`, `node_id`, `save_to_project=false`. | Direct-run semantics documented/test-proven. | `RunNodeUseCase` only loads/resolves saved project when `project_id and save_to_project`. | Missing. | API test comparing `save_to_project=true` and `false`. | `app/application/use_cases/run_node.py`. | User may expect saved node inputs/edges to resolve but direct run uses raw payload. |
| EC-027 | Generic catalog models | FR-021, FR-022 | P1 | Exact model ID must be preserved. | Run generic catalog node with exact `model_id`. | Adapter receives exact ID. | Generic path uses `model_spec.source == "catalog"` and passes `model_id` to adapter. | Covered: `tests/test_generic_wavespeed_runner.py`. | None. | Already covered. | Low current risk. |
| EC-028 | Generic catalog models | FR-022 | P1 | Media/list field coercion min/max. | Use catalog model with `images` min/max, too few/many assets. | Clear error before provider call. | `model_input_resolver.coerce_field_value` handles min/max and asset lists. | Covered for multiple image list; min/max needs stronger direct tests. | Add min/max list tests using catalog field fixture. | `model_input_resolver.py`. | Bad request to provider or surprising UI behavior. |
| EC-029 | Local utility nodes | FR-023, FR-012, FR-013 | P1 | Runnable local utilities are excluded from workflow planning and job queueing. | Add `video_last_frame` or `stitch_video`, then queue selected/whole graph. | Runnable local utilities should run locally or documented as single-node only. | `workflow_resolver.is_runnable` returns false for all `UTILITY_NODE_TYPES`; `run_manager.queue_node_run` rejects any utility node. `RunNodeUseCase` can run runnable local utilities. | Weak: tests prove cataloged runnable and direct runner works, not workflow/job behavior. | API tests for selected local utility run/queue semantics. | `workflow_resolver.py`, `run_manager.py`, `RunNodeUseCase`. | UI/graph promises “runnable” utility but workflow queue skips/rejects it. |
| EC-030 | Local utility nodes | FR-023 | P2 | `stitch_video` fewer than two videos. | Run stitch with one or zero videos. | Clear local utility error. | `run_stitch_video` raises `Stitch Videos requires at least two video inputs.` | Covered: resolver collection and runner tests; fewer-than-two direct test missing. | Direct runner/API test for fewer-than-two. | `local_utility_runner.py`. | User sees confusing failure if not caught in UI. |
| EC-031 | Local utility nodes | FR-023 | P2 | Stitch order includes unknown/duplicate order keys. | Set `videos_order` to unknown values or duplicate keys. | Clear validation or deterministic documented fallback. | `ordered_list_values` silently falls back; no validation of bad order entries. | Missing. | Unit test for invalid/duplicate `videos_order`. | `workflow_resolver.py`, frontend ordered-list UI. | Stitched output order differs from user intent. |
| EC-032 | Local utility nodes | FR-023 | P2 | Missing ffmpeg or corrupt/non-video input. | Run `video_last_frame`/`stitch_video` with corrupt file or unavailable ffmpeg. | Clear error and output cleanup. | Exceptions are wrapped; stitch unlinks output on failure. Missing ffmpeg path not directly tested. | Weak: happy path with mocked stitch exists. | Unit tests for corrupt video and monkeypatched ffmpeg failure. | `local_utility_runner.py`. | Local utility fails with poor error or leaves partial files. |
| EC-033 | Workflow execution | FR-012 | P1 | Selected/from-node/whole-graph ordering. | Plan/run graph with two dependent model nodes. | Topological dependency order. | `topological_sort`, `select_node_ids`, `build_execution_plan`, and run manager use ordered IDs. | Covered: `tests/test_v7.py`, `tests/test_v10_utility_nodes.py`. | None. | Already covered. | Low current risk. |
| EC-034 | Workflow execution | FR-012, FR-013 | P1 | Partial failure and cancellation. | Run workflow where second step fails or cancel after first step. | Terminal job/run history records failure/cancel; remaining queued nodes skipped on cancel. | `run_manager._execute_workflow_job` checks cancel at step boundary; failures mark current node. | Covered for cancel; partial failure covered in variants, not general workflow. | Add workflow partial-failure API test. | `run_manager.py`, `workflow.py`. | Mixed node statuses can confuse rerun/recovery. |
| EC-035 | Jobs / run manager | FR-013 | P1 | Overlapping queued jobs on same project nodes. | Queue selected node job, then queue workflow/from-node containing same node. | Second queue should block or explicitly allow conflict. | `_assert_no_active_node_job` only runs for direct node jobs; workflow queue only blocks active whole-graph jobs. | Missing. | Run manager test for overlapping selected/from-node/whole-graph jobs. | `app/services/run_manager.py`. | Race conditions and lost outputs from concurrent writes. |
| EC-036 | Jobs / run manager | FR-013, FR-014 | P2 | Retry failed/cancelled job creates new ID; clear completed jobs. | Fail/cancel job, retry, clear terminal jobs. | New job ID; terminal jobs removed from memory only. | Implemented in `retry_job` and `clear_completed`. | Covered: `tests/test_v7.py`. | None. | Already covered. | Low current risk. |
| EC-037 | Jobs / server restart | FR-014 | P3 | In-memory jobs disappear on restart but terminal run history persists. | Complete job, restart server, list jobs and project runs. | Jobs gone; `project.runs` still contains terminal snapshot. | Design is in-memory; `_write_project_run_history` persists terminal snapshots. | Weak: run history write covered, restart behavior not tested. | Integration test simulating new `LocalRunManager` after saved run. | `run_manager.py`. | User may expect active job recovery. |
| EC-038 | Cost guard/settings | FR-017 | P1 | Invalid thresholds and incompatible overrides. | PUT settings with negative/ordered thresholds or wrong model override. | 400/422 clear errors. | Pydantic and `project_validation.validate_project_settings` enforce. | Covered: `tests/test_v4.py`, `tests/test_clean_architecture.py`. | None. | Already covered. | Low current risk. |
| EC-039 | Cost guard/settings | FR-017 | P2 | Backend USD values accidentally converted to MYR. | Save settings or estimates after frontend displays MYR. | Persisted/backend values remain USD. | Backend uses `estimated_base_cost_usd`; frontend converts display only with `DISPLAY_USD_TO_MYR_RATE`. | Missing direct regression test. | Frontend/API test verifying saved settings and estimate are USD numeric values. | `frontend/src/main.jsx`, `cost_estimator.py`. | Cost guard thresholds could block/allow wrong runs. |
| EC-040 | Import/export/duplicate | FR-018 | P2 | Invalid import JSON or too-large import. | POST malformed JSON body or multipart over limit. | 400 for invalid JSON, size-limit error for oversized import. | `projects.py:read_import_payload` checks size and JSON parse; route catches errors. | Missing direct tests for malformed raw JSON and size limit. | API tests for invalid JSON and import size cap. | `app/routers/projects.py`, `portable_project.py`. | Poor import UX or memory pressure. |
| EC-041 | Import/export/duplicate | FR-018 | P1 | Local filesystem paths stripped and bad edges/node types rejected. | Export/import project with local paths, bad node type, missing edge node. | Sanitized or rejected with warnings/errors. | `portable_project` sanitizes local paths; validates node types/settings/edges. | Covered: `tests/test_v5.py`. | None. | Already covered. | Low current risk. |
| EC-042 | Templates and recipes | FR-019, FR-020 | P1 | Applying same recipe repeatedly can duplicate edge IDs. | Apply a built-in recipe to an existing project twice. | New nodes and edges all have unique IDs. | `recipe_store.apply_recipe_to_project` remaps duplicate node IDs, but appends cloned edges without assigning new edge IDs. | Missing. | API/unit test applying same recipe twice and asserting unique node/edge IDs. | `app/services/recipe_store.py`. | React Flow/project graph can behave unpredictably with duplicate edge IDs. |
| EC-043 | Templates and recipes | FR-019 | P2 | Built-in template deletion and unknown template/recipe. | DELETE built-in template, GET/POST unknown IDs. | Built-in delete 400; unknown IDs 404. | Template store raises `BuiltinTemplateError`/not found; recipe route maps `RecipeError` to 404. | Covered for built-in template delete; unknown recipe/template weak. | Add unknown template/recipe API tests. | `templates.py`, `recipes.py`. | UI may show generic failure for missing library entries. |
| EC-044 | Artifacts / lineage | FR-024 | P1 | Cyclic artifact lineage recurses forever. | Create two assets whose `lineage.source_artifact_ids` point to each other, then GET lineage. | API detects cycle and stops with warning/path. | `artifact_service.artifact_lineage_tree` recurses without visited set. | Missing. | Unit/API lineage cycle test. | `app/services/artifact_service.py`. | Stack overflow / request failure on bad imported/manual data. |
| EC-045 | Artifacts / branching | FR-016, FR-024 | P1 | Video artifact can branch to `video_effect` with `video` input, but runner expects `image`. | Branch a video artifact to `video_effect`, then run resulting node. | Branch compatibility should match runner schema or reject. | `branching.COMPATIBLE_TARGETS[AssetKind.video][NodeType.video_effect] = ["video"]`; `prepare_video_effect_inputs` calls `resolve_image_input`. | Missing. | Branch/run test for video artifact to video_effect. | `app/services/branching.py`, `app/services/node_runner.py`. | Branch creates a node that cannot run. |
| EC-046 | Artifacts / metadata | FR-024 | P2 | Invalid artifact rating. | POST rating 0 or 6. | Clear 400. | `artifact_service.rate_artifact` validates 1..5. | Missing direct route test. | API test for rating bounds. | `app/routers/artifacts.py`, `artifact_service.py`. | Bad metadata if validation regresses. |
| EC-047 | Variants/comparisons/run snapshots | FR-025 | P1 | Variant queue can queue prompt-card clones instead of model clones when prompt-source clones are inserted. | Create variants for a prompted model where `cloned_incoming_prompt_edges` adds extra Prompt Card nodes. | Only generated model clones should be queued. | `variant_runner.queue_variant_set` appends clone plus optional prompt clones, then iterates `project.nodes[-len(payloads):]`; this slice can include prompt clones instead of all model clones. | Weak: variant cost/partial failures covered, prompt-clone queue target not directly covered. | Unit test for prompt-card variant cloning with `variant_count > 1`. | `app/services/variant_runner.py`. | Variant jobs fail or skip because wrong node type is queued. |
| EC-048 | Variants/comparisons/run snapshots | FR-025 | P1 | Clone-node creates predictable IDs that can collide. | Call `/runs/{run_id}/clone-node` repeatedly after manually creating an ID matching `node_clone_{len+1}`. | Clone ID should use `new_id("node")` or ensure uniqueness. | `run_snapshots.py:clone_run_node` sets `clone.id = f"{node.id}_clone_{len(project.nodes)+1}"` without checking existing IDs. | Missing. | API test for clone-node ID collision. | `app/routers/run_snapshots.py`. | Duplicate node IDs break graph rendering and persistence. |
| EC-049 | Frontend API errors | FR-026, FR-027 | P2 | API error detail object/list displays poorly. | Mock API returning `{detail:{errors:[...]}}` or FastAPI validation shape. | Status shows actionable message. | `frontend/src/api/client.js` handles string/list/detail.errors; `main.jsx` still has duplicate `detailMessage` helper. | Weak: smoke tests mostly happy path. | Playwright test for failed upload/run/settings error message. | `frontend/src/api/client.js`, `frontend/src/main.jsx`. | User cannot correct bad workflows. |
| EC-050 | Frontend stale UI | FR-002, FR-013, FR-027 | P2 | Save/delete/job refresh leaves stale selected node or project. | Delete active project, save after stale local state, or refresh jobs after project switch. | UI selection and status follow active project. | Frontend updates active project after delete in smoke mock; deeper stale save/job paths need verification. | Weak: project delete smoke covered. | Playwright test for switching project while jobs poll or save in progress. | `frontend/src/main.jsx`. | Editing wrong project or confusing job panel. |
| EC-051 | Frontend output preview | FR-015 | P3 | Unknown output URL type or unavailable URL. | Node output URL has no extension, 404 URL, or local path. | UI shows safe link/fallback and actions do not crash. | `PreviewMedia` chooses media by extension; otherwise renders link/fallback. | Weak: smoke covers image open/copy/download only. | Playwright tests for video/audio/text/unknown output URLs and failed copy/download. | `frontend/src/main.jsx`. | Output appears broken despite valid raw response. |
| EC-052 | Model catalog data | FR-021, FR-022 | P2 | Schema-visible but unsupported/excluded model becomes executable. | Pick excluded catalog model ID and run generic node. | Execution blocked. | Registry and node runner use catalog exclusions/denylist. | Covered by registry/catalog tests; route-level run test weak. | API run test for excluded catalog ID. | `registry.py`, `node_runner.py`. | Unverified provider calls and cost surprises. |

## Highest Priority Fix Plan

Recommended implementation order for P0/P1 only:

1. **Block arbitrary local path exfiltration**: reject raw local filesystem paths in `node_runner.resolve_asset_input` and `model_input_resolver.resolve_asset_value` unless they resolve under the configured upload directory and belong to a project asset. Covers EC-004.
2. **Harden local utility path resolution**: normalize `/uploads/...` references, reject traversal, and enforce containment under `settings.upload_dir`. Covers EC-005.
3. **Expand private URL blocking**: use `ipaddress` resolution for loopback, private, link-local, multicast, and unspecified addresses across `model_input_resolver`, `node_runner`, and `local_utility_runner`. Covers EC-006.
4. **Prevent concurrent project/node job collisions**: block or serialize overlapping workflow and node jobs for the same project/node set. Covers EC-003 and EC-035.
5. **Resolve runnable local utility semantics**: decide whether `video_last_frame` and `stitch_video` are runnable in workflow/job mode; then make planner, run manager, and UI consistent. Covers EC-029.
6. **Fix recipe and snapshot clone ID uniqueness**: use generated IDs/remap edges when applying recipes and cloning run nodes. Covers EC-042 and EC-048.
7. **Fix branch compatibility for `video_effect`**: align `branching.py` with the actual `prepare_video_effect_inputs` schema or update the runner/schema if video input is intended. Covers EC-045.
8. **Fix variant clone queue target slicing**: track clone IDs explicitly instead of slicing `project.nodes`. Covers EC-047.
9. **Add lineage cycle protection**: pass a visited set through `artifact_lineage_tree`. Covers EC-044.
10. **Improve stored-project error isolation**: skip/report corrupt project files in list and return clear load errors. Covers EC-001 and EC-002.

## Missing Test Plan

### Backend unit tests

Add or extend:

* `tests/test_asset_resolution.py`
  * Reject raw local paths outside upload dir.
  * Reject full private/link-local URL set.
  * Reject/allow uploaded project asset local paths according to final policy.
* `tests/test_local_utility_security.py` or `tests/test_v10_utility_nodes.py`
  * Reject `/uploads/../...` traversal.
  * `stitch_video` fewer than two inputs.
  * Invalid/duplicate `videos_order`.
  * Missing ffmpeg/corrupt video error cleanup.
* `tests/test_project_store_edge_cases.py`
  * Malformed JSON during list.
  * Schema-invalid stored project during load.
  * Concurrent save conflict or transaction behavior.
* `tests/test_workflow_edge_compatibility.py`
  * Duplicate edge warning/block.
  * Incompatible media connection at planning time.
  * Stale local output URL/file.
* `tests/test_recipe_store.py`
  * Applying same recipe twice yields unique node and edge IDs.
* `tests/test_artifact_service.py`
  * Lineage cycle protection.
  * Rating bounds if not covered through API.
* `tests/test_variant_runner.py`
  * Prompt-card variants queue only model clones.
* `tests/test_run_snapshots.py`
  * Clone-node ID collision avoidance.

### Backend API tests

Add or extend:

* `tests/test_assets_api.py`
  * Unsupported upload type behavior.
  * Mismatched MIME/suffix behavior.
  * WaveSpeed upload failure cleanup.
* `tests/test_runs_api_edge_cases.py`
  * Missing API key through `/api/runs/node`.
  * `save_to_project=true` vs `false`.
  * Excluded catalog model through API.
  * Saved node status becomes error on malformed provider output.
* `tests/test_import_api_edge_cases.py`
  * Invalid raw JSON body.
  * Multipart import too large.
* `tests/test_jobs_overlap.py`
  * Queue node then overlapping workflow/from-node.
  * Queue workflow then overlapping node.
* `tests/test_artifacts_api.py`
  * Invalid rating route.
  * Branch video artifact to `video_effect` should reject or run depending on chosen policy.
* `tests/test_templates_recipes_api.py`
  * Unknown template and recipe IDs.

### Frontend Playwright tests

Add or extend `frontend/tests/ui-smoke.spec.js` or split a new `ui-errors.spec.js`:

* Failed upload displays backend message.
* Failed run displays saved node error/status message.
* Settings validation error is visible and actionable.
* Duplicate filenames remain distinguishable in the Assets rail.
* Switching/deleting project while job polling is active does not show stale project state.
* Output previews render image, video, audio, text, and unknown URL fallbacks.
* Copy/Open/Download unavailable URL actions do not crash the UI.
* Local utility run/queue UI behavior matches final backend policy.

## Closure Notes

The edge cases in this audit have been addressed without changing public route paths, request/response shapes, project JSON shape, model IDs, or the WaveSpeed adapter/node-runner boundaries. Production-hardening work outside the documented MVP remains out of scope unless it is added to `requirements.md` or a future task.
