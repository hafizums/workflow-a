import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import Asset, CanvasEdge, CanvasNode, CostGuardSettings, NodeStatus, NodeType, Project, ProjectSettings, RunJob
from app.services import project_store
from app.services.run_manager import LocalRunManager, RunManagerError, run_manager


async def fake_run_wavespeed_node(**kwargs):
    target_node = kwargs.get("target_node")
    node_id = target_node.id if target_node else "node"
    url = f"https://example.com/{node_id}.png"
    return {"outputs": [url]}, [url], [Asset(kind="image", filename=f"{node_id}.png", public_url=url)]


class RunManagerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.project_ids: list[str] = []

    async def asyncTearDown(self):
        for project_id in self.project_ids:
            try:
                await project_store.delete_project(project_id)
            except project_store.ProjectStoreError:
                pass

    async def save_project(self, project: Project) -> Project:
        saved = await project_store.save_project(project)
        self.project_ids.append(saved.id)
        return saved

    async def test_queue_node_job_transitions_to_success_and_writes_history(self):
        project = await self.save_project(
            Project(nodes=[CanvasNode(id="node_a", type=NodeType.text_to_image, title="A", inputs={"prompt": "Test"})])
        )
        manager = LocalRunManager()
        job = await manager.queue_node_run(project.id, "node_a")
        self.assertEqual(job.status, "queued")

        with patch("app.services.run_manager.node_runner.run_wavespeed_node", fake_run_wavespeed_node):
            await manager._execute_job(job)

        self.assertEqual(job.status, "success")
        self.assertEqual(job.progress_current, 1)
        persisted = await project_store.load_project(project.id)
        self.assertEqual(persisted.nodes[0].status, "success")
        self.assertEqual(persisted.runs[0]["job_id"], job.id)
        self.assertEqual(persisted.runs[0]["status"], "success")

    async def test_queued_job_can_be_cancelled(self):
        project = await self.save_project(
            Project(nodes=[CanvasNode(id="node_a", type=NodeType.text_to_image, title="A", inputs={"prompt": "Test"})])
        )
        manager = LocalRunManager()
        job = await manager.queue_node_run(project.id, "node_a")
        cancelled = await manager.cancel_job(job.id)
        self.assertEqual(cancelled.status, "cancelled")
        persisted = await project_store.load_project(project.id)
        self.assertEqual(persisted.runs[0]["status"], "cancelled")

    async def test_running_workflow_honors_cancel_requested_between_steps(self):
        project = await self.save_project(
            Project(
                nodes=[
                    CanvasNode(id="node_a", type=NodeType.text_to_image, title="A", inputs={"prompt": "A"}, output_urls=["https://example.com/a.png"]),
                    CanvasNode(id="node_b", type=NodeType.image_to_image, title="B", inputs={"prompt": "B"}),
                ],
                edges=[CanvasEdge(id="edge_ab", source_node_id="node_a", target_node_id="node_b", target_input="image")],
            )
        )
        manager = LocalRunManager()
        job = await manager.queue_workflow_run(project.id, mode="whole_graph")

        async def fake_execute_step(project, node, job, resolved_inputs=None):
            node.status = NodeStatus.success
            if node.id == "node_a":
                job.status = "cancel_requested"

        with patch.object(manager, "_execute_single_node", fake_execute_step):
            await manager._execute_job(job)

        self.assertEqual(job.status, "cancelled")
        self.assertEqual(job.progress_current, 1)
        persisted = await project_store.load_project(project.id)
        node_b = next(node for node in persisted.nodes if node.id == "node_b")
        self.assertEqual(node_b.status, "skipped")

    async def test_failed_job_can_be_retried_with_new_id(self):
        project = await self.save_project(
            Project(nodes=[CanvasNode(id="node_a", type=NodeType.text_to_image, title="A", inputs={"prompt": "Test"})])
        )
        manager = LocalRunManager()
        job = await manager.queue_node_run(project.id, "node_a")
        job.status = "error"
        retry = await manager.retry_job(job.id)
        self.assertNotEqual(job.id, retry.id)
        self.assertEqual(retry.status, "queued")

    async def test_cost_guard_blocked_node_is_not_queued(self):
        project = await self.save_project(
            Project(
                nodes=[CanvasNode(id="node_a", type=NodeType.text_to_image, title="A", inputs={"prompt": "Test"})],
                settings=ProjectSettings(cost_guard=CostGuardSettings(enabled=True, block_at_usd_per_run=0.001)),
            )
        )
        manager = LocalRunManager()
        with self.assertRaisesRegex(RunManagerError, "block threshold"):
            await manager.queue_node_run(project.id, "node_a")
        self.assertEqual(manager.jobs, {})

    async def test_workflow_job_uses_plan_step_count(self):
        project = await self.save_project(
            Project(
                nodes=[
                    CanvasNode(id="node_a", type=NodeType.text_to_image, title="A", inputs={"prompt": "A"}, output_urls=["https://example.com/a.png"]),
                    CanvasNode(id="node_b", type=NodeType.image_to_image, title="B", inputs={"prompt": "B"}),
                ],
                edges=[CanvasEdge(id="edge_ab", source_node_id="node_a", target_node_id="node_b", target_input="image")],
            )
        )
        manager = LocalRunManager()
        job = await manager.queue_workflow_run(project.id, mode="whole_graph")
        self.assertEqual(job.progress_total, 2)
        self.assertEqual(job.node_ids, ["node_a", "node_b"])

    async def test_list_jobs_filters_and_clear_completed_only_terminal_jobs(self):
        project = await self.save_project(
            Project(nodes=[CanvasNode(id="node_a", type=NodeType.text_to_image, title="A", inputs={"prompt": "Test"})])
        )
        manager = LocalRunManager()
        queued = await manager.queue_node_run(project.id, "node_a")
        done = RunJob(project_id=project.id, kind="single_node", status="success", node_ids=["node_done"])
        manager.jobs[done.id] = done

        filtered = await manager.list_jobs(project_id=project.id, status="queued")
        self.assertEqual([job.id for job in filtered], [queued.id])

        result = await manager.clear_completed()
        self.assertEqual(result["cleared"], 1)
        self.assertIn(queued.id, manager.jobs)
        self.assertNotIn(done.id, manager.jobs)


class JobsApiTests(unittest.TestCase):
    def setUp(self):
        run_manager.jobs.clear()
        self.client = TestClient(app)

    def tearDown(self):
        run_manager.jobs.clear()

    def test_jobs_endpoints_are_available(self):
        response = self.client.get("/api/jobs")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

        response = self.client.get("/api/jobs/missing")
        self.assertEqual(response.status_code, 404)

        response = self.client.delete("/api/jobs/completed")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cleared"], 0)


if __name__ == "__main__":
    unittest.main()
