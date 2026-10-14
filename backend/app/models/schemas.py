"""Request and response models for the pin-resolution API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    purpose: str = Field(default="", max_length=240)

    @field_validator("name", "purpose")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("Project name is required.")
        return value


class ProjectOut(BaseModel):
    id: int
    name: str
    purpose: str
    created_at: str


class ProjectPage(BaseModel):
    items: list[ProjectOut]
    total: int
    limit: int
    offset: int


class ResolutionIn(BaseModel):
    node_version: str = Field(default="", max_length=20_000)
    nvmrc: str = Field(default="", max_length=20_000)
    package_json: str = Field(default="", max_length=100_000)
    installed: list[str] = Field(default_factory=list, max_length=200)

    @field_validator("installed")
    @classmethod
    def installed_items(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in values:
            text = item.strip()
            if len(text) > 64:
                raise ValueError("Each installed version must be 64 characters or fewer.")
            cleaned.append(text)
        return cleaned


class ResolutionInputs(BaseModel):
    node_version: str
    nvmrc: str
    package_json: str
    installed: list[str]


class ResolutionOut(BaseModel):
    id: int
    project_id: int
    source: str
    requested: str
    status: str
    matched: str | None
    caller_exit_code: int
    explanation: str
    matches: list[str]
    ignored: list[str]
    inputs: ResolutionInputs
    lts_snapshot: str
    lts_latest_codename: str
    lts_latest_major: int
    created_at: str


class ResolutionPage(BaseModel):
    items: list[ResolutionOut]
    total: int
    limit: int
    offset: int


class VersionOut(BaseModel):
    version: str


class HealthOut(BaseModel):
    status: str
