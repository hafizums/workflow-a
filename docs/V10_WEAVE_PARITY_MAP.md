# V10 Weave-Style Workflow Parity Map

V10 adds workflow capabilities inspired by AI canvas production tools while keeping this app's own identity and WaveSpeed-only execution model.

| Capability | Why it matters | V10 implementation | Uses WaveSpeed? | Status |
| --- | --- | --- | --- | --- |
| Tool/model nodes | Gives users executable AI steps on the canvas. | Registry-backed WaveSpeed model specs and node execution. | Yes, for AI execution. | Implemented |
| Utility nodes | Lets users organize intent and artifacts without running AI. | Local prompt, style, character, selector, compare, variant, reroute, note, group, and export nodes. | No, local only. | Implemented |
| Branch from output | Turns any useful result into the start of a new path. | Artifact branch API creates compatible child nodes from artifact IDs. | No for branching; child nodes may run WaveSpeed. | Implemented |
| Fan-out variants | Enables rapid exploration from one setup. | Variant sets clone a source node with seed, suffix, list, range, or template changes and queue runs. | Yes, each variant run uses WaveSpeed. | Implemented |
| Multi-model compare | Lets users compare compatible model choices. | Comparison sets queue compatible enabled models and group outputs. | Yes, each comparison run uses WaveSpeed. | Implemented |
| Seed/prompt variation compare | Helps evaluate prompt and stochastic differences. | Variant parameters support seed and prompt strategies; outputs group under a variant set. | Yes. | Implemented |
| Pick winner / promote artifact | Captures the chosen deliverable for downstream use. | Artifact role API plus variant and comparison winner endpoints mark assets as winners. | No, metadata only. | Implemented |
| Artifact lineage | Makes outputs traceable and reusable. | Assets store source project, node, run/job, model, input keys, and source artifact IDs. | No, metadata only. | Implemented |
| Prompt/style cards | Reusable creative intent reduces repeated typing. | Utility nodes resolve prompt/style text into connected model inputs. | No, local only. | Implemented |
| Character/reference cards | Keeps recurring subject or voice direction consistent. | Character cards output reusable description text and reference metadata. | No, local only. | Implemented |
| Workflow recipes | Starts users from useful production graphs. | Built-in WaveSpeed-only recipes create or apply project graphs. | Mixed: local graph setup, WaveSpeed when run. | Implemented |
| Export bundle | Packages final deliverables with context. | Export package manifest records selected artifacts, URLs, roles, and lineage. | No, manifest only. | Implemented |
| Run snapshots | Supports repeatable and inspectable runs. | Queued and direct runs store model, inputs, outputs, cost estimate, status, warnings, and errors. | No, metadata only. | Implemented |
| Cost snapshot | Helps keep exploration bounded. | Existing cost guard and run snapshots store estimated cost metadata. | No, local estimate only. | Implemented |
| Reusable project templates | Lets users preserve graph layouts. | Existing template system remains, alongside V10 recipes. | No, local project metadata. | Implemented |

## V11 Catalog Scale-Out Note

V11 keeps these V10 workflow features and makes model selection catalog-aware. Generic `generic_wavespeed` nodes can use exact WaveSpeed model IDs from the normalized workbook catalog, while variants and model comparisons can group compatible models by output kind, required fields, and capability metadata rather than only old node types.

## Product Guardrails

We replicate workflow functionality, not Figma, Weave, or Weavy branding, visual identity, trade dress, proprietary UI, or marketing copy.

All executable AI tools must be WaveSpeed-only. Local utility nodes may orchestrate prompts, references, selection, comparison, packaging, lineage, and cost metadata, but they must not call OpenAI, Anthropic, Google, Runway, Replicate, Fal, Figma, Weave, Weavy, or any other non-WaveSpeed AI API.

Every executable capability maps to either an enabled WaveSpeed model in the registry/catalog or a local utility node. Runtime-excluded catalog rows are not shown as runnable add-node cards; they remain inspectable through `/api/model-catalog/excluded` until schema, output handling, and cost behavior are supported.
