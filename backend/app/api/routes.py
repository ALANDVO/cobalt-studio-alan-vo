"""HTTP routes for projects and Node pin resolutions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.core.version import product_version
from app.models.schemas import (
    HealthOut,
    ProjectIn,
    ProjectOut,
    ProjectPage,
    ResolutionIn,
    ResolutionOut,
    ResolutionPage,
    VersionOut,
)
from app.services.store import CatalogRejected, NoPinRejected, add_resolution, create_project, get_project, get_resolution, list_projects, list_resolutions

router = APIRouter()
_STATUSES = {"satisfied", "missing", "invalid"}


@router.get("/api/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(status="ok")


@router.get("/api/version", response_model=VersionOut)
def version() -> VersionOut:
    return VersionOut(version=product_version())


@router.post("/api/projects", response_model=ProjectOut, status_code=201)
def post_project(body: ProjectIn, request: Request) -> ProjectOut:
    return ProjectOut(**create_project(request.app.state.database_path, body))


@router.get("/api/projects", response_model=ProjectPage)
def get_projects(
    request: Request,
    q: str = Query(default="", max_length=80),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ProjectPage:
    return ProjectPage(**list_projects(request.app.state.database_path, q, limit, offset))


@router.get("/api/projects/{project_id}", response_model=ProjectOut)
def get_one_project(project_id: int, request: Request) -> ProjectOut:
    project = get_project(request.app.state.database_path, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return ProjectOut(**project)


@router.post("/api/projects/{project_id}/resolutions", response_model=ResolutionOut, status_code=201)
def post_resolution(project_id: int, body: ResolutionIn, request: Request) -> ResolutionOut:
    try:
        stored = add_resolution(request.app.state.database_path, project_id, body)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found.") from None
    except CatalogRejected as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except NoPinRejected as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return ResolutionOut(**stored)


@router.get("/api/projects/{project_id}/resolutions", response_model=ResolutionPage)
def get_resolutions(
    project_id: int,
    request: Request,
    status: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ResolutionPage:
    if status and status not in _STATUSES:
        raise HTTPException(status_code=422, detail="Status filter must be satisfied, missing, or invalid.")
    page = list_resolutions(request.app.state.database_path, project_id, status, limit, offset)
    if page is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return ResolutionPage(**page)


@router.get("/api/resolutions/{resolution_id}", response_model=ResolutionOut)
def get_one_resolution(resolution_id: int, request: Request) -> ResolutionOut:
    stored = get_resolution(request.app.state.database_path, resolution_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Resolution not found.")
    return ResolutionOut(**stored)
