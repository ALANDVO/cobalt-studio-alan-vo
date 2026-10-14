"""Choose one Node pin and the highest installed release that satisfies it.

Precedence is deliberate: ``.node-version``, then ``.nvmrc``, then
``package.json`` ``engines.node``. A higher file that does not parse does not
fall through. A missing install is a recorded result, not an exception.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.core.lts import SNAPSHOT, latest
from app.core.semver import (
    AliasConstraint,
    Constraint,
    LtsAnyConstraint,
    LtsLineConstraint,
    RequestError,
    Version,
    parse_request,
)


class NoPin(ValueError):
    """None of the three pin inputs contained a version request."""


@dataclass(frozen=True)
class Resolution:
    source: str
    requested: str
    status: str
    matched: str | None
    caller_exit_code: int
    explanation: str
    matches: tuple[str, ...]
    ignored: tuple[str, ...]
    lts_snapshot: str
    lts_latest_codename: str
    lts_latest_major: int


def resolve_pin(
    *,
    node_version: str | None,
    nvmrc: str | None,
    package_json: str | None,
    installed: list[Version],
) -> Resolution:
    node_line = pin_line(node_version)
    nvm_line = pin_line(nvmrc)
    engines_state, engines_value = engines_node(package_json)
    codename, major = latest()
    base = {
        "lts_snapshot": SNAPSHOT,
        "lts_latest_codename": codename,
        "lts_latest_major": major,
    }

    if node_line is not None:
        ignored = _ignored("node-version", nvm_line, engines_state)
        return _from_request("node-version", node_line, installed, ignored, base)
    if nvm_line is not None:
        ignored = _ignored("nvmrc", None, engines_state)
        return _from_request("nvmrc", nvm_line, installed, ignored, base)
    if engines_state == "invalid":
        return Resolution(
            source="engines",
            requested="",
            status="invalid",
            matched=None,
            caller_exit_code=2,
            explanation=engines_value or "package.json could not be read.",
            matches=(),
            ignored=("Did not read a Node pin from package.json.",),
            **base,
        )
    if engines_state == "present":
        return _from_request("engines", engines_value or "", installed, (), base)
    raise NoPin("No version pin was provided. Add .node-version, .nvmrc, or package.json engines.node.")


def pin_line(text: str | None) -> str | None:
    if text is None:
        return None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        return line or None
    return None


def engines_node(package_json: str | None) -> tuple[str, str | None]:
    """Return ``absent``, ``present``, or ``invalid`` plus the pin or error text."""
    if package_json is None or not package_json.strip():
        return "absent", None
    try:
        data = json.loads(package_json)
    except json.JSONDecodeError:
        return "invalid", "package.json is not valid JSON, so engines.node was not read."
    if not isinstance(data, dict):
        return "invalid", "package.json must be a JSON object."
    engines = data.get("engines")
    if engines is None:
        return "absent", None
    if not isinstance(engines, dict):
        return "invalid", "package.json engines must be an object."
    node = engines.get("node")
    if node is None:
        return "absent", None
    if not isinstance(node, str) or not node.strip():
        return "invalid", "package.json engines.node must be a non-empty string."
    return "present", node.strip()


def _ignored(source: str, nvm_line: str | None, engines_state: str) -> tuple[str, ...]:
    notes: list[str] = []
    if source != "nvmrc" and nvm_line is not None:
        notes.append("Ignored .nvmrc because a higher-precedence pin is set.")
    if source != "engines" and engines_state == "present":
        notes.append("Ignored package.json engines.node because a higher-precedence pin is set.")
    if source != "engines" and engines_state == "invalid":
        notes.append("Ignored package.json because it could not be read.")
    return tuple(notes)


def _from_request(
    source: str,
    requested: str,
    installed: list[Version],
    ignored: tuple[str, ...],
    base: dict[str, str | int],
) -> Resolution:
    label = _source_label(source)
    try:
        constraint = parse_request(requested)
    except RequestError as exc:
        return Resolution(
            source=source,
            requested=requested,
            status="invalid",
            matched=None,
            caller_exit_code=2,
            explanation=f"{label} pin {requested!r} was not accepted: {exc} Later pin files were not used.",
            matches=(),
            ignored=ignored + ("Did not fall through to a lower-precedence pin.",),
            **base,
        )
    chosen = constraint.select(installed)
    labels = tuple(sorted((item.label() for item in chosen), reverse=True))
    if not labels:
        return Resolution(
            source=source,
            requested=requested,
            status="missing",
            matched=None,
            caller_exit_code=0,
            explanation=_missing_text(label, requested, constraint),
            matches=(),
            ignored=ignored,
            **base,
        )
    matched = labels[0]
    return Resolution(
        source=source,
        requested=requested,
        status="satisfied",
        matched=matched,
        caller_exit_code=0,
        explanation=f"{label} pin {requested} matches installed {matched}. "
        + _rule_text(constraint)
        + " The highest matching release was selected.",
        matches=labels,
        ignored=ignored,
        **base,
    )


def _source_label(source: str) -> str:
    if source == "node-version":
        return ".node-version"
    if source == "nvmrc":
        return ".nvmrc"
    return "package.json engines.node"


def _rule_text(constraint: Constraint) -> str:
    if isinstance(constraint, LtsAnyConstraint):
        return f"lts/* uses the {constraint.name} line (major {constraint.major}) from the {SNAPSHOT} snapshot."
    if isinstance(constraint, LtsLineConstraint):
        return f"lts/{constraint.name} is major {constraint.major} in the {SNAPSHOT} snapshot."
    if isinstance(constraint, AliasConstraint):
        return f"Alias {constraint.name} means the highest installed release."
    return "The pin was compared as a version or range."


def _missing_text(label: str, requested: str, constraint: Constraint) -> str:
    detail = _rule_text(constraint)
    return (
        f"{label} pin {requested} is valid, and no installed release satisfies it. {detail} "
        "Caller exit code stays 0 so a shell that only records this result does not abort."
    )
