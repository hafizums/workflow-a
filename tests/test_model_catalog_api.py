from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_catalog_summary_and_capabilities_routes():
    summary = client.get("/api/model-catalog/summary")
    assert summary.status_code == 200
    assert summary.json()["counts"]["models"] >= 900

    capabilities = client.get("/api/model-catalog/capabilities")
    assert capabilities.status_code == 200
    assert len(capabilities.json()) >= 50


def test_model_id_path_routes_with_slashes():
    model = client.get("/api/model-catalog/models/alibaba/happyhorse-1.0/text-to-video")
    assert model.status_code == 200
    assert model.json()["model_id"] == "alibaba/happyhorse-1.0/text-to-video"

    schema = client.get("/api/model-catalog/models/akool/video-face-swap/schema")
    assert schema.status_code == 200
    assert any(field["name"] == "video" for field in schema.json())


def test_enabled_models_include_catalog_and_utility():
    response = client.get("/api/models?enabled_only=true")
    assert response.status_code == 200
    models = response.json()
    ids = {model["id"] for model in models}
    assert "alibaba/happyhorse-1.0/text-to-video" in ids
    assert "local/utility/prompt_card" in ids
