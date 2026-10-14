"""HTTP tests for the project and resolution workflow."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "cobalt.sqlite"))
    with TestClient(app) as test_client:
        yield test_client


def _project(client: TestClient, name: str = "eval-dashboard", purpose: str = "model evaluation UI") -> dict:
    response = client.post("/api/projects", json={"name": name, "purpose": purpose})
    assert response.status_code == 201, response.text
    return response.json()


def test_health_and_version_match_the_version_file(client: TestClient):
    assert client.get("/api/health").json() == {"status": "ok"}
    expected = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert client.get("/api/version").json() == {"version": expected}


def test_create_resolve_and_read_back_a_satisfied_pin(client: TestClient):
    project = _project(client)
    created = client.post(
        f"/api/projects/{project['id']}/resolutions",
        json={
            "node_version": "20.18\n",
            "nvmrc": "lts/*",
            "package_json": json.dumps({"engines": {"node": ">=18"}}),
            "installed": ["v20.18.0", "20.18.2", "20.19.0", "24.11.0"],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["source"] == "node-version"
    assert body["status"] == "satisfied"
    assert body["matched"] == "20.18.2"
    assert body["caller_exit_code"] == 0
    assert body["inputs"]["installed"] == ["v20.18.0", "20.18.2", "20.19.0", "24.11.0"]
    fetched = client.get(f"/api/resolutions/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["explanation"] == body["explanation"]
    listed = client.get(f"/api/projects/{project['id']}/resolutions")
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == body["id"]


def test_missing_install_is_stored_and_filterable(client: TestClient):
    project = _project(client, name="training-ui")
    missing = client.post(
        f"/api/projects/{project['id']}/resolutions",
        json={"node_version": "22.14.0", "installed": ["20.11.1"]},
    )
    assert missing.status_code == 201
    assert missing.json()["status"] == "missing"
    assert missing.json()["caller_exit_code"] == 0
    invalid = client.post(
        f"/api/projects/{project['id']}/resolutions",
        json={"nvmrc": "nope", "installed": ["20.11.1"]},
    )
    assert invalid.status_code == 201
    assert invalid.json()["status"] == "invalid"
    only_missing = client.get(f"/api/projects/{project['id']}/resolutions?status=missing")
    assert only_missing.json()["total"] == 1
    assert only_missing.json()["items"][0]["status"] == "missing"
    bad_filter = client.get(f"/api/projects/{project['id']}/resolutions?status=nope")
    assert bad_filter.status_code == 422


def test_validation_errors_do_not_write_a_resolution(client: TestClient):
    project = _project(client)
    empty = client.post(f"/api/projects/{project['id']}/resolutions", json={"installed": ["20.0.0"]})
    assert empty.status_code == 422
    assert "No version pin" in empty.json()["detail"]
    partial = client.post(
        f"/api/projects/{project['id']}/resolutions",
        json={"node_version": "20", "installed": ["20"]},
    )
    assert partial.status_code == 422
    assert "full release" in partial.json()["detail"]
    history = client.get(f"/api/projects/{project['id']}/resolutions")
    assert history.json()["total"] == 0


def test_unknown_records_and_project_search_pagination(client: TestClient):
    assert client.get("/api/projects/99").status_code == 404
    assert client.post("/api/projects/99/resolutions", json={"node_version": "20"}).status_code == 404
    assert client.get("/api/resolutions/4").status_code == 404
    first = _project(client, name="alpha notes")
    second = _project(client, name="beta_eval")
    page = client.get("/api/projects?limit=1&offset=0")
    assert page.json()["total"] == 2
    assert page.json()["items"][0]["id"] == second["id"]
    rest = client.get("/api/projects?limit=1&offset=1")
    assert rest.json()["items"][0]["id"] == first["id"]
    beyond = client.get("/api/projects?limit=10&offset=20")
    assert beyond.json()["items"] == []
    assert beyond.json()["total"] == 2
    quoted = client.get("/api/projects", params={"q": "' OR 1=1 --"})
    assert quoted.status_code == 200
    assert quoted.json()["total"] == 0
    wildcard = client.get("/api/projects", params={"q": "%"})
    assert wildcard.json()["total"] == 0
    underscore = client.get("/api/projects", params={"q": "beta_eval"})
    assert [item["name"] for item in underscore.json()["items"]] == ["beta_eval"]
    blank = client.post("/api/projects", json={"name": "   ", "purpose": "x"})
    assert blank.status_code == 422


def test_audit_log_records_project_and_resolution_together(client: TestClient):
    project = _project(client, name="audit-target")
    created = client.post(
        f"/api/projects/{project['id']}/resolutions",
        json={"node_version": "20.11.1", "installed": ["20.11.1"]},
    )
    assert created.status_code == 201
    connection = sqlite3.connect(client.app.state.database_path)
    try:
        rows = connection.execute(
            "SELECT action, entity, entity_id, detail FROM audit_log ORDER BY id"
        ).fetchall()
    finally:
        connection.close()
    assert [row[0] for row in rows] == ["create", "resolve"]
    assert rows[0][1] == "project"
    assert rows[0][2] == project["id"]
    detail = json.loads(rows[1][3])
    assert detail["status"] == "satisfied"
    assert detail["project_id"] == project["id"]
    connection = sqlite3.connect(client.app.state.database_path)
    try:
        count = connection.execute("SELECT COUNT(*) FROM resolutions").fetchone()[0]
    finally:
        connection.close()
    assert count == 1
