import { expect, test } from "@playwright/test";

const now = "2026-06-13T00:00:00Z";

const categories = [
  { id: "image", label: "Image" },
  { id: "utility", label: "Utility" }
];

const models = [
  {
    id: "wavespeed-ai/z-image/turbo",
    label: "Text to Image",
    display_name: "Text to Image",
    node_type: "text_to_image",
    category: "image",
    output_kind: "image",
    enabled: true,
    source: "curated",
    default_model_id: "wavespeed-ai/z-image/turbo",
    estimated_base_cost_usd: 0.005,
    fields: [
      { name: "prompt", type: "textarea", required: true, description: "Prompt text." },
      { name: "size", type: "string", default: "1024*1024", description: "Output size." }
    ]
  },
  {
    id: "local/utility/prompt_card",
    label: "Prompt Card",
    display_name: "Prompt Card",
    node_type: "prompt_card",
    category: "utility",
    output_kind: "other",
    enabled: true,
    source: "utility",
    estimated_base_cost_usd: 0,
    fields: [
      { name: "text", type: "textarea", required: true, default: "", description: "Reusable prompt text." },
      { name: "negative_prompt", type: "textarea", default: "", description: "Reusable negative prompt." }
    ]
  },
  {
    id: "local/utility/asset_input",
    label: "Asset Input",
    display_name: "Asset Input",
    node_type: "asset_input",
    category: "utility",
    output_kind: "other",
    enabled: true,
    source: "utility",
    estimated_base_cost_usd: 0,
    fields: [
      { name: "asset_id", type: "asset_id", required: true, description: "Project artifact selected or uploaded from this node." }
    ]
  }
];

function project(id = "proj-1", name = "Smoke Project", options = {}) {
  const includePromptEdge = options.includePromptEdge !== false;
  const outputUrl = options.outputUrl ?? "/uploads/smoke-output.png";
  return {
    id,
    name,
    description: "Browser smoke test project",
    nodes: [
      {
        id: "node-image",
        type: "text_to_image",
        title: "Text to Image",
        model_id: "wavespeed-ai/z-image/turbo",
        inputs: { size: "1024*1024" },
        x: 120,
        y: 100,
        status: "success",
        output_urls: [outputUrl],
        output_asset_ids: [],
        last_run: {
          output_urls: [outputUrl],
          raw_output: { id: "run-1", status: "completed" }
        },
        created_at: now,
        updated_at: now
      },
      {
        id: "node-prompt",
        type: "prompt_card",
        title: "Prompt Card",
        inputs: { text: "A clean product shot", negative_prompt: "" },
        x: -240,
        y: 100,
        status: "idle",
        output_urls: [],
        output_asset_ids: [],
        created_at: now,
        updated_at: now
      }
    ],
    edges: includePromptEdge ? [
      {
        id: "edge-prompt-image",
        source_node_id: "node-prompt",
        target_node_id: "node-image",
        source_output: "output",
        target_input: "prompt"
      }
    ] : [],
    assets: options.assets ?? [
      {
        id: "asset-1",
        kind: "image",
        filename: "smoke-input.png",
        content_type: "image/png",
        local_path: "",
        public_url: "/uploads/smoke-input.png",
        wavespeed_url: "",
        metadata: {},
        created_at: now
      }
    ],
    runs: [],
    settings: {
      model_overrides: {},
      cost_guard: {
        enabled: false,
        warn_at_usd_per_run: null,
        block_at_usd_per_run: null,
        max_workflow_run_usd: null,
        block_on_unknown_cost: false
      }
    },
    created_at: now,
    updated_at: now
  };
}

async function installApiMocks(page, options = {}) {
  let projects = [project("proj-1", "Smoke Project", options), project("proj-2", "Fallback Project")];
  let activeProject = projects[0];
  let deleteCalled = false;
  let lastSavedProject = null;
  let queuedWorkflow = false;

  await page.route("**/api/projects", async (route) => {
    const request = route.request();
    if (request.method() === "GET") {
      await route.fulfill({ json: projects });
      return;
    }
    if (request.method() === "POST") {
      activeProject = project("proj-new", "Default Model Canvas Workflow");
      projects = [activeProject, ...projects];
      await route.fulfill({ json: activeProject });
      return;
    }
    await route.fallback();
  });

  await page.route("**/api/projects/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const id = url.pathname.split("/").pop();
    if (request.method() === "GET") {
      await route.fulfill({ json: projects.find((item) => item.id === id) || activeProject });
      return;
    }
    if (request.method() === "PUT") {
      activeProject = await request.postDataJSON();
      activeProject.id = id;
      lastSavedProject = activeProject;
      projects = projects.map((item) => item.id === id ? activeProject : item);
      await route.fulfill({ json: activeProject });
      return;
    }
    if (request.method() === "DELETE") {
      deleteCalled = true;
      projects = projects.filter((item) => item.id !== id);
      activeProject = projects[0] || project("proj-empty", "Empty Project");
      await route.fulfill({ json: { ok: true } });
      return;
    }
    await route.fallback();
  });

  await page.route("**/api/models?enabled_only=true", async (route) => route.fulfill({ json: models }));
  await page.route("**/api/categories", async (route) => route.fulfill({ json: categories }));
  await page.route("**/api/jobs/workflow/all", async (route) => {
    queuedWorkflow = true;
    await route.fulfill({
      json: {
        id: "job-1",
        project_id: activeProject.id,
        kind: "workflow",
        status: "queued",
        node_ids: activeProject.nodes.map((node) => node.id),
        created_at: now,
        updated_at: now
      }
    });
  });
  await page.route("**/api/jobs?limit=50", async (route) => route.fulfill({ json: [] }));
  await page.route("**/api/assets/upload?*", async (route) => {
    if (options.uploadError) {
      await route.fulfill({ status: 400, json: { detail: options.uploadError } });
      return;
    }
    const uploaded = {
      id: "asset-uploaded",
      kind: "image",
      filename: "uploaded-smoke.png",
      content_type: "image/png",
      local_path: "",
      public_url: "/uploads/uploaded-smoke.png",
      wavespeed_url: "",
      metadata: {},
      created_at: now
    };
    activeProject.assets = [uploaded, ...(activeProject.assets || [])];
    projects = projects.map((item) => item.id === activeProject.id ? activeProject : item);
    await route.fulfill({ json: uploaded });
  });
  await page.route("**/uploads/**", async (route) => {
    await route.fulfill({
      contentType: "image/png",
      body: Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=",
        "base64"
      )
    });
  });

  return {
    wasDeleteCalled: () => deleteCalled,
    lastSavedProject: () => lastSavedProject,
    wasWorkflowQueued: () => queuedWorkflow
  };
}

test("loads a project and exposes output/cost/debug UI", async ({ page }) => {
  await installApiMocks(page);

  await page.goto("/");

  await expect(page.getByText("Text to Image").first()).toBeVisible();
  await expect(page.getByText("Prompt Card").first()).toBeVisible();
  await page.getByText("Models", { exact: true }).click();
  await expect(page.getByText("1 models")).toBeVisible();
  await page.getByText("Utility", { exact: true }).click();
  await expect(page.getByText("2 utilities")).toBeVisible();
  await expect(page.getByRole("button", { name: /Run.*RM0\.0203/ })).toBeVisible();
  await expect(page.getByRole("link", { name: "Open", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Copy URL" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Download" })).toBeVisible();
  await expect(page.getByText("Raw response")).toBeVisible();
});

test("adds catalog and utility nodes from rail menus", async ({ page }) => {
  await installApiMocks(page);

  await page.goto("/");
  await expect(page.locator(".workflow-node")).toHaveCount(2);

  await page.getByText("Models", { exact: true }).click();
  await page.getByRole("button", { name: /Add Node/ }).first().click();
  await expect(page.locator(".workflow-node")).toHaveCount(3);

  await page.getByText("Utility", { exact: true }).click();
  await page.locator(".library-card", { hasText: "Asset Input" }).getByRole("button", { name: /Add Node/ }).click();
  await expect(page.locator(".workflow-node")).toHaveCount(4);
  await expect(page.getByText("Asset Input").first()).toBeVisible();
});

test("uploads a local asset from the Assets rail", async ({ page }) => {
  await installApiMocks(page);

  await page.goto("/");
  await page.getByText("Assets", { exact: true }).click();
  await page.locator('input[type="file"]').setInputFiles({
    name: "uploaded-smoke.png",
    mimeType: "image/png",
    buffer: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=",
      "base64"
    )
  });

  await expect(page.getByText("uploaded-smoke.png", { exact: true })).toBeVisible();
});

test("shows upload API errors in the status bar", async ({ page }) => {
  await installApiMocks(page, { uploadError: "Upload failed in test" });

  await page.goto("/");
  await page.getByText("Assets", { exact: true }).click();
  await page.locator('input[type="file"]').setInputFiles({
    name: "broken-upload.png",
    mimeType: "image/png",
    buffer: Buffer.from("not-an-image")
  });

  await expect(page.getByText("Upload failed in test")).toBeVisible();
});

test("distinguishes duplicate asset filenames by asset id", async ({ page }) => {
  await installApiMocks(page, {
    assets: [
      { id: "asset-duplicate-a", kind: "image", filename: "same-name.png", content_type: "image/png", public_url: "/uploads/a.png", metadata: {}, created_at: now },
      { id: "asset-duplicate-b", kind: "image", filename: "same-name.png", content_type: "image/png", public_url: "/uploads/b.png", metadata: {}, created_at: now }
    ]
  });

  await page.goto("/");
  await page.getByText("Assets", { exact: true }).click();

  await expect(page.getByText("same-name.png")).toHaveCount(2);
  await expect(page.getByText(/asset-duplicate-a/)).toBeVisible();
  await expect(page.getByText(/asset-duplicate-b/)).toBeVisible();
});

test("renders a safe fallback for unknown output URL types", async ({ page }) => {
  await installApiMocks(page, { outputUrl: "https://example.com/generated-output" });

  await page.goto("/");

  await expect(page.getByRole("link", { name: "Open output" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Open", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Copy URL" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Download" })).toBeVisible();
});

test("persists dragged node positions on save", async ({ page }) => {
  const mocks = await installApiMocks(page);

  await page.goto("/");
  const promptNode = page.locator(".workflow-node", { hasText: "Prompt Card" });
  await expect(promptNode).toBeVisible();
  const box = await promptNode.locator(".drag-handle").boundingBox();
  expect(box).not.toBeNull();

  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + 120, box.y + box.height / 2 + 40, { steps: 8 });
  await page.mouse.up();

  await page.getByText("Project", { exact: true }).click();
  await page.getByRole("button", { name: /Save/ }).click();

  await expect.poll(() => mocks.lastSavedProject()?.nodes?.find((node) => node.id === "node-prompt")?.x).not.toBe(-240);
});

test("autosaves project metadata edits", async ({ page }) => {
  const mocks = await installApiMocks(page);

  await page.goto("/");
  await page.getByText("Project", { exact: true }).click();
  await page.getByLabel("Name").fill("Autosave Smoke Project");

  await expect(page.getByText("Unsaved changes")).toBeVisible();
  await expect.poll(() => mocks.lastSavedProject()?.name, { timeout: 5000 }).toBe("Autosave Smoke Project");
  await expect(page.locator(".autosave-indicator")).toContainText("Saved");

  await page.reload();
  await page.getByText("Project", { exact: true }).click();
  await expect(page.getByLabel("Name")).toHaveValue("Autosave Smoke Project");
});

test("creates and saves a manual prompt edge", async ({ page }) => {
  const mocks = await installApiMocks(page, { includePromptEdge: false });

  await page.goto("/");
  const sourceHandle = page.getByTestId("node-handle-node-prompt-output-source");
  const targetHandle = page.getByTestId("node-handle-node-image-prompt-target");
  await expect(sourceHandle).toBeVisible();
  await expect(targetHandle).toBeVisible();

  await sourceHandle.click();
  await expect(page.getByText("Output selected. Click a target input handle to connect.")).toBeVisible();
  await targetHandle.click();
  await expect(page.getByText("Connected nodes.")).toBeVisible();

  await page.getByText("Project", { exact: true }).click();
  await page.getByRole("button", { name: /Save/ }).click();

  await expect.poll(() => mocks.lastSavedProject()?.edges?.[0]?.target_input).toBe("prompt");

  await page.reload();
  await expect(page.locator(".react-flow__edge")).toHaveCount(1);
});

test("queues whole-graph workflow from the Run rail", async ({ page }) => {
  const mocks = await installApiMocks(page);

  await page.goto("/");
  await page.getByText("Run", { exact: true }).click();
  await page.getByRole("button", { name: "Queue Whole Graph" }).click();

  await expect.poll(() => mocks.wasWorkflowQueued()).toBe(true);
  await expect(page.getByText("Workflow job queued.")).toBeVisible();
});

test("project delete is reachable from the Project rail popover", async ({ page }) => {
  const mocks = await installApiMocks(page);
  page.on("dialog", (dialog) => dialog.accept());

  await page.goto("/");
  await page.getByText("Project", { exact: true }).click();
  await page.getByRole("button", { name: /Delete/ }).click();

  await expect.poll(() => mocks.wasDeleteCalled()).toBe(true);
  await expect(page.getByLabel("Name")).toHaveValue("Fallback Project");
});
