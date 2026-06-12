from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.storage import read_json, write_json
from app.schemas import Project

PROJECT_ID_RE = re.compile(r"^project_[a-f0-9]{12}$")


class ProjectStoreError(Exception):
    """Base error for local project persistence."""


class InvalidProjectIdError(ProjectStoreError):
    pass


class ProjectNotFoundError(ProjectStoreError):
    pass


def _project_path(project_id: str, settings: Settings | None = None) -> Path:
    if not PROJECT_ID_RE.fullmatch(project_id):
        raise InvalidProjectIdError("Invalid project ID")
    settings = settings or get_settings()
    return settings.project_dir / f"{project_id}.json"


async def list_projects(settings: Settings | None = None) -> list[Project]:
    settings = settings or get_settings()
    projects: list[Project] = []
    for path in settings.project_dir.glob("*.json"):
        data = await read_json(path, None)
        if data:
            projects.append(Project.model_validate(data))
    return sorted(projects, key=lambda project: project.updated_at, reverse=True)


async def load_project(project_id: str, settings: Settings | None = None) -> Project:
    path = _project_path(project_id, settings)
    data = await read_json(path, None)
    if data is None:
        raise ProjectNotFoundError("Project not found")
    return Project.model_validate(data)


async def save_project(project: Project, settings: Settings | None = None) -> Project:
    project.updated_at = datetime.now(timezone.utc)
    await write_json(_project_path(project.id, settings), project.model_dump(mode="json"))
    return project


async def delete_project(project_id: str, settings: Settings | None = None) -> None:
    path = _project_path(project_id, settings)
    if not path.exists():
        raise ProjectNotFoundError("Project not found")
    path.unlink()
