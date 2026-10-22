"""Transactional project and resolution storage."""

import json
import sqlite3
from datetime import datetime, timezone

from app.core.binary import BinaryInfo
from app.core.db import session
from app.core.resolver import NoPin, Resolution, resolve_pin
from app.core.semver import RequestError, parse_installed
from app.models.schemas import ProjectIn, ResolutionIn


class CatalogRejected(ValueError):
    """The installed-version list is not usable."""


class NoPinRejected(ValueError):
    """The request did not include a pin."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_project(path: str, body: ProjectIn) -> dict:
    stamp = utc_now()
    with session(path) as connection:
        cursor = connection.execute(
            "INSERT INTO projects (name, purpose, created_at) VALUES (?, ?, ?)",
            (body.name, body.purpose, stamp),
        )
        project_id = int(cursor.lastrowid)
        _audit(connection, "create", "project", project_id, {"name": body.name}, stamp)
    project = get_project(path, project_id)
    if project is None:
        raise RuntimeError("Project insert did not persist.")
    return project


def get_project(path: str, project_id: int) -> dict | None:
    with session(path) as connection:
        row = connection.execute(
            "SELECT id, name, purpose, created_at FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
    return dict(row) if row else None


def list_projects(path: str, query: str, limit: int, offset: int) -> dict:
    pattern = _like_contains(query.strip())
    where = ""
    args: list[object] = []
    if query.strip():
        where = "WHERE name LIKE ? ESCAPE '\\'"
        args.append(pattern)
    with session(path) as connection:
        total = int(connection.execute(f"SELECT COUNT(*) FROM projects {where}", args).fetchone()[0])
        rows = connection.execute(
            f"SELECT id, name, purpose, created_at FROM projects {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            [*args, limit, offset],
        ).fetchall()
    return {"items": [dict(row) for row in rows], "total": total, "limit": limit, "offset": offset}


def add_resolution(path: str, project_id: int, body: ResolutionIn) -> dict:
    if get_project(path, project_id) is None:
        raise KeyError(project_id)
    try:
        catalog = parse_installed(body.installed)
    except RequestError as exc:
        raise CatalogRejected(str(exc)) from exc
    try:
        result = resolve_pin(
            node_version=body.node_version,
            nvmrc=body.nvmrc,
            package_json=body.package_json,
            installed=catalog,
            base_path=body.base_path if hasattr(body, "base_path") else None,
        )
    except NoPin as exc:
        raise NoPinRejected(str(exc)) from exc
    return _insert_resolution(path, project_id, body, result)


def list_resolutions(path: str, project_id: int, status: str, limit: int, offset: int) -> dict | None:
    if get_project(path, project_id) is None:
        return None
    where = "WHERE project_id = ?"
    args: list[object] = [project_id]
    if status:
        where += " AND status = ?"
        args.append(status)
    with session(path) as connection:
        total = int(connection.execute(f"SELECT COUNT(*) FROM resolutions {where}", args).fetchone()[0])
        rows = connection.execute(
            f"SELECT * FROM resolutions {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            [*args, limit, offset],
        ).fetchall()
    return {"items": [_resolution_dict(row) for row in rows], "total": total, "limit": limit, "offset": offset}


def get_resolution(path: str, resolution_id: int) -> dict | None:
    with session(path) as connection:
        row = connection.execute("SELECT * FROM resolutions WHERE id = ?", (resolution_id,)).fetchone()
    return _resolution_dict(row) if row else None


def _insert_resolution(path: str, project_id: int, body: ResolutionIn, result: Resolution) -> dict:
    stamp = utc_now()
    installed = [item.strip() for item in body.installed if item.strip()]
    binary_info_json = json.dumps(
        {
            version: {
                "version": info.version,
                "path": info.path,
                "architecture": info.architecture,
                "format": info.format,
                "interpreter": info.interpreter,
                "compatible": info.compatible,
                "reason": info.reason,
            }
            for version, info in result.binary_info.items()
        }
    )
    with session(path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO resolutions (
              project_id, source, requested, status, matched, caller_exit_code, explanation,
              matches_json, ignored_json, installed_json, node_version, nvmrc, package_json,
              lts_snapshot, lts_latest_codename, lts_latest_major, binary_info_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                result.source,
                result.requested,
                result.status,
                result.matched,
                result.caller_exit_code,
                result.explanation,
                json.dumps(list(result.matches)),
                json.dumps(list(result.ignored)),
                json.dumps(installed),
                body.node_version,
                body.nvmrc,
                body.package_json,
                result.lts_snapshot,
                result.lts_latest_codename,
                result.lts_latest_major,
                binary_info_json,
                stamp,
            ),
        )
        resolution_id = int(cursor.lastrowid)
        _audit(
            connection,
            "resolve",
            "resolution",
            resolution_id,
            {"project_id": project_id, "status": result.status, "source": result.source},
            stamp,
        )
    stored = get_resolution(path, resolution_id)
    if stored is None:
        raise RuntimeError("Resolution insert did not persist.")
    return stored


def _audit(connection: sqlite3.Connection, action: str, entity: str, entity_id: int, detail: dict, stamp: str) -> None:
    connection.execute(
        "INSERT INTO audit_log (action, entity, entity_id, detail, created_at) VALUES (?, ?, ?, ?, ?)",
        (action, entity, entity_id, json.dumps(detail, sort_keys=True), stamp),
    )


def _resolution_dict(row: sqlite3.Row) -> dict:
    installed = json.loads(row["installed_json"])
    binary_info_json = row["binary_info_json"] if "binary_info_json" in row.keys() else "{}"
    binary_info_raw = json.loads(binary_info_json)
    binary_info = {}
    for version, info in binary_info_raw.items():
        binary_info[version] = {
            "version": info.get("version"),
            "path": info.get("path"),
            "architecture": info.get("architecture"),
            "format": info.get("format"),
            "interpreter": info.get("interpreter"),
            "compatible": info.get("compatible"),
            "reason": info.get("reason"),
        }
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "source": row["source"],
        "requested": row["requested"],
        "status": row["status"],
        "matched": row["matched"],
        "caller_exit_code": row["caller_exit_code"],
        "explanation": row["explanation"],
        "matches": json.loads(row["matches_json"]),
        "ignored": json.loads(row["ignored_json"]),
        "inputs": {
            "node_version": row["node_version"],
            "nvmrc": row["nvmrc"],
            "package_json": row["package_json"],
            "installed": installed,
        },
        "binary_info": binary_info,
        "lts_snapshot": row["lts_snapshot"],
        "lts_latest_codename": row["lts_latest_codename"],
        "lts_latest_major": row["lts_latest_major"],
        "created_at": row["created_at"],
    }


def _like_contains(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
