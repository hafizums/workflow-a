from __future__ import annotations

from app.schemas import Project, ProjectSettings
from app.services.project_validation import validate_edges_reference_nodes, validate_project_settings


class ImportValidationPolicy:
    """Facade for project import and portable-project validation rules."""

    def validate_settings(self, settings: ProjectSettings) -> ProjectSettings:
        return validate_project_settings(settings)

    def validate_project_edges(self, project: Project) -> None:
        validate_edges_reference_nodes(project.edges, {node.id for node in project.nodes})

