import pytest

from app.schemas import Asset, AssetKind, Project
from app.services import catalog_repository
from app.services.model_input_resolver import ModelInputResolverError, prepare_model_inputs
from app.services.registry import get_model_by_id


class FakeAdapter:
    def __init__(self):
        self.uploads = []

    async def upload_file(self, path):
        self.uploads.append(str(path))
        return f"https://files.example/{path.name}"


@pytest.mark.asyncio
async def test_asset_url_list_handles_newline_and_comma_inputs():
    catalog_model = next(
        (
            model
            for model in catalog_repository.list_catalog_models()
            for field in model.fields
            if field.type == "asset_url_list"
        ),
        None,
    )
    if catalog_model is None:
        pytest.skip("Workbook has no asset_url_list fields")
    list_field = next(field for field in catalog_model.fields if field.type == "asset_url_list")
    required_inputs = {
        field.name: sample_value_for_field(field)
        for field in catalog_model.fields
        if field.required and field.name != list_field.name
    }
    prepared = await prepare_model_inputs(
        adapter=FakeAdapter(),
        model=catalog_model,
        inputs={**required_inputs, list_field.name: "https://example.com/a.png,\nhttps://example.com/b.png"},
        project=Project(),
    )
    assert prepared[list_field.name] == ["https://example.com/a.png", "https://example.com/b.png"]


@pytest.mark.asyncio
async def test_plural_media_asset_field_is_treated_as_list():
    model = get_model_by_id("wavespeed-ai/ai-clothes-changer")
    prepared = await prepare_model_inputs(
        adapter=FakeAdapter(),
        model=model,
        inputs={
            "image": "https://example.com/person.png",
            "clothes_images": "https://example.com/a.png, https://example.com/b.png",
        },
        project=Project(),
    )
    assert prepared["clothes_images"] == ["https://example.com/a.png", "https://example.com/b.png"]


def sample_value_for_field(field):
    if field.type in {"asset_url", "file_url"}:
        return "https://example.com/input.png"
    if field.type == "asset_url_list":
        return "https://example.com/input.png"
    if field.type == "boolean":
        return False
    if field.type == "integer":
        return 1
    if field.type == "number":
        return 1.0
    if field.type == "select" and field.options:
        return field.options[0]
    if field.type == "json":
        return {}
    return "x"


@pytest.mark.asyncio
async def test_local_asset_path_is_uploaded(tmp_path):
    path = tmp_path / "input.png"
    path.write_bytes(b"fake")
    project = Project(
        assets=[
            Asset(
                id="asset_img",
                kind=AssetKind.image,
                filename="input.png",
                local_path=str(path),
            )
        ]
    )
    model = get_model_by_id("alibaba/happyhorse-1.0/image-to-video")
    prepared = await prepare_model_inputs(
        adapter=FakeAdapter(),
        model=model,
        inputs={"prompt": "move", "image": "asset_img"},
        project=project,
    )
    assert prepared["image"].startswith("https://files.example/")


@pytest.mark.asyncio
async def test_localhost_url_is_rejected():
    model = get_model_by_id("alibaba/happyhorse-1.0/image-to-video")
    with pytest.raises(ModelInputResolverError):
        await prepare_model_inputs(
            adapter=FakeAdapter(),
            model=model,
            inputs={"prompt": "move", "image": "http://localhost:8000/uploads/a.png"},
            project=Project(),
        )
