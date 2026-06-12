from __future__ import annotations

from app.schemas import ArtifactRole, ExportPackageArtifact, ExportPackageManifest, Project


class ExportPackageError(ValueError):
    pass


def create_export_package(project: Project, asset_ids: list[str] | None = None) -> ExportPackageManifest:
    selected_ids = set(asset_ids or [])
    if selected_ids:
        artifacts = [asset for asset in project.assets if asset.id in selected_ids]
    else:
        artifacts = [
            asset
            for asset in project.assets
            if asset.view.role in {ArtifactRole.winner, ArtifactRole.export} or asset.view.pinned
        ]
    if not artifacts:
        raise ExportPackageError("No winner, pinned, export, or explicitly selected artifacts are available to package.")

    manifest = ExportPackageManifest(
        project_id=project.id,
        artifacts=[
            ExportPackageArtifact(
                asset_id=asset.id,
                role=asset.view.role,
                kind=asset.kind,
                filename=asset.filename,
                url=asset.wavespeed_url or asset.public_url or asset.local_path,
                source_node_id=asset.lineage.source_node_id,
                source_model_id=asset.lineage.source_model_id,
                lineage=asset.lineage.model_dump(mode="json"),
            )
            for asset in artifacts
        ],
    )
    project.export_packages.insert(0, manifest)
    return manifest


def get_export_package(project: Project, package_id: str) -> ExportPackageManifest:
    package = next((item for item in project.export_packages if item.id == package_id), None)
    if package is None:
        raise ExportPackageError("Export package not found")
    return package
