"""Match a Node pin against installed releases.

The grammar covers the pin text this studio accepts. Prerelease tags, build
metadata, and partial hyphen ranges are rejected instead of guessed.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from app.core.lts import latest, major_for

_NUM = r"(?:0|[1-9]\d*)"
_PART = rf"(?:{_NUM}|x|X|\*)"
_VERSION_PREFIX = re.compile(rf"^[vV]?({_NUM})(?:\.({_PART}))?(?:\.({_PART}))?")
_EXACT = re.compile(rf"^[vV]?({_NUM})\.({_NUM})\.({_NUM})$")
_OPS = (">=", "<=", ">", "<", "=", "^", "~")


class RequestError(ValueError):
    """The pin or catalog entry is not in the supported grammar."""


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int

    def label(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class Partial:
    major: int
    minor: int | None
    patch: int | None
    minor_omitted: bool
    patch_omitted: bool
    wild_minor: bool
    wild_patch: bool

    def padded(self) -> Version:
        return Version(self.major, 0 if self.minor is None else self.minor, 0 if self.patch is None else self.patch)


Predicate = Callable[[Version], bool]


class Constraint:
    """A parsed pin. Subclasses return every installed release that satisfies it."""

    code = "range"


class RangeConstraint(Constraint):
    def __init__(self, clauses: list[list[Predicate]]):
        self.clauses = clauses

    def select(self, catalog: list[Version]) -> list[Version]:
        return [item for item in catalog if any(all(pred(item) for pred in clause) for clause in self.clauses)]


class AliasConstraint(Constraint):
    code = "alias"

    def __init__(self, name: str):
        self.name = name

    def select(self, catalog: list[Version]) -> list[Version]:
        return list(catalog)


class LtsLineConstraint(Constraint):
    code = "lts-line"

    def __init__(self, name: str, major: int):
        self.name = name
        self.major = major

    def select(self, catalog: list[Version]) -> list[Version]:
        return [item for item in catalog if item.major == self.major]


class LtsAnyConstraint(Constraint):
    code = "lts-any"

    def __init__(self) -> None:
        codename, major = latest()
        self.name = codename
        self.major = major

    def select(self, catalog: list[Version]) -> list[Version]:
        return [item for item in catalog if item.major == self.major]


def parse_installed(values: list[str]) -> list[Version]:
    found: list[Version] = []
    seen: set[Version] = set()
    for raw in values:
        text = raw.strip()
        if not text:
            raise RequestError("Installed catalog contains a blank version.")
        match = _EXACT.fullmatch(text)
        if match is None:
            raise RequestError(
                f"Installed version {text!r} must be a full release such as 20.11.1. Partial versions belong in the pin, not the catalog."
            )
        version = Version(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if version not in seen:
            seen.add(version)
            found.append(version)
    return found


def parse_request(text: str) -> Constraint:
    raw = text.strip()
    if not raw:
        raise RequestError("Version pin is empty.")
    if len(raw) > 200:
        raise RequestError("Version pin is longer than 200 characters.")
    lowered = raw.lower()
    if lowered in {"node", "stable"}:
        return AliasConstraint(lowered)
    if lowered in {"system", "iojs", "current", "unstable"}:
        raise RequestError(f"Alias {raw!r} is not resolved in this checkpoint.")
    if lowered == "lts/*":
        return LtsAnyConstraint()
    if lowered.startswith("lts/"):
        name = lowered.split("/", 1)[1].strip()
        major = major_for(name)
        if major is None or not name:
            raise RequestError(f"Unknown LTS codename {name!r}. Known names are the bundled snapshot.")
        return LtsLineConstraint(name, major)
    return RangeConstraint(_parse_range(raw))


def _parse_range(text: str) -> list[list[Predicate]]:
    parts = [part.strip() for part in text.split("||")]
    if any(not part for part in parts):
        raise RequestError("Version range has an empty || clause.")
    return [_parse_clause(part) for part in parts]


def _parse_clause(text: str) -> list[Predicate]:
    if " - " in text:
        return [_parse_hyphen(text)]
    predicates: list[Predicate] = []
    pos = 0
    length = len(text)
    while pos < length:
        if text[pos].isspace():
            pos += 1
            continue
        predicate, pos = _read_comparator(text, pos)
        predicates.append(predicate)
    if not predicates:
        raise RequestError("Version range clause is empty.")
    return predicates


def _parse_hyphen(text: str) -> Predicate:
    left, right = (part.strip() for part in text.split(" - ", 1))
    if not left or not right or " " in left or " " in right or "||" in text:
        raise RequestError("A hyphen range must be two full versions, such as 18.0.0 - 20.11.1.")
    start = _require_exact(left)
    end = _require_exact(right)
    if start > end:
        raise RequestError("Hyphen range is reversed.")
    return lambda version, start=start, end=end: start <= version <= end


def _require_exact(token: str) -> Version:
    partial = _parse_partial(token)
    if partial.minor_omitted or partial.patch_omitted or partial.wild_minor or partial.wild_patch:
        raise RequestError(
            f"{token!r} is not a full major.minor.patch version. Partial hyphen ranges are unsupported."
        )
    return partial.padded()


def _read_comparator(text: str, pos: int) -> tuple[Predicate, int]:
    operator = ""
    for candidate in _OPS:
        if text.startswith(candidate, pos):
            operator = candidate
            pos += len(candidate)
            break
    while pos < len(text) and text[pos].isspace():
        pos += 1
    body, pos = _read_body(text, pos)
    return _predicate(operator, body), pos


def _read_body(text: str, pos: int) -> tuple[str, int]:
    if pos >= len(text):
        raise RequestError("Version comparator is missing a version.")
    if text[pos] in {"*", "x", "X"}:
        end = pos + 1
        if end < len(text) and not text[end].isspace():
            raise RequestError(f"Unsupported version syntax near {text[pos:pos + 24]!r}.")
        return text[pos], end
    match = _VERSION_PREFIX.match(text[pos:])
    if match is None:
        raise RequestError(f"Cannot read a version near {text[pos:pos + 24]!r}.")
    end = pos + match.end()
    if end < len(text) and not text[end].isspace():
        raise RequestError(
            f"Unsupported version syntax near {text[pos:pos + 24]!r}. Prerelease tags and build metadata are rejected."
        )
    return text[pos:end], end


def _parse_partial(token: str) -> Partial:
    if token in {"*", "x", "X"}:
        raise RequestError("Wildcard is not a numbered version.")
    match = _VERSION_PREFIX.fullmatch(token)
    if match is None:
        raise RequestError(f"Cannot read version {token!r}.")
    minor_raw = match.group(2)
    patch_raw = match.group(3)
    wild_minor = minor_raw is not None and not minor_raw.isdigit()
    wild_patch = patch_raw is not None and not patch_raw.isdigit()
    if wild_minor and patch_raw is not None and patch_raw.isdigit():
        raise RequestError(f"{token!r} uses a wildcard minor with a numbered patch.")
    return Partial(
        major=int(match.group(1)),
        minor=None if minor_raw is None or wild_minor else int(minor_raw),
        patch=None if patch_raw is None or wild_patch else int(patch_raw),
        minor_omitted=minor_raw is None,
        patch_omitted=patch_raw is None or wild_minor,
        wild_minor=wild_minor,
        wild_patch=wild_patch,
    )


def _predicate(operator: str, body: str) -> Predicate:
    wildcard = body in {"*", "x", "X"}
    if wildcard:
        if operator:
            raise RequestError(f"Operator {operator} cannot be combined with {body!r}.")
        return lambda _version: True
    partial = _parse_partial(body)
    if operator in {"^", "~"} and (partial.wild_minor or partial.wild_patch):
        raise RequestError(f"{operator}{body} mixes an operator with a wildcard. Use a bare version such as 18 or 18.x.")
    if operator == "^":
        return _caret(partial)
    if operator == "~":
        return _tilde(partial)
    if operator == "":
        return _bare(partial)
    if partial.wild_minor or partial.wild_patch:
        raise RequestError(f"{operator}{body} mixes a comparator with a wildcard.")
    target = partial.padded()
    if operator == "=":
        return lambda version, target=target: version == target
    if operator == ">":
        return lambda version, target=target: version > target
    if operator == ">=":
        return lambda version, target=target: version >= target
    if operator == "<":
        return lambda version, target=target: version < target
    if operator == "<=":
        return lambda version, target=target: version <= target
    raise RequestError(f"Unsupported operator {operator!r}.")


def _bare(partial: Partial) -> Predicate:
    if partial.wild_minor or partial.minor_omitted:
        major = partial.major
        return lambda version, major=major: version.major == major
    if partial.wild_patch or partial.patch_omitted:
        if partial.minor is None:
            raise RequestError(f"Version {partial.major} is missing a minor component.")
        major, minor = partial.major, partial.minor
        return lambda version, major=major, minor=minor: version.major == major and version.minor == minor
    target = partial.padded()
    return lambda version, target=target: version == target


def _caret(partial: Partial) -> Predicate:
    lower = partial.padded()
    if lower.major > 0:
        upper = Version(lower.major + 1, 0, 0)
    elif lower.minor > 0:
        upper = Version(0, lower.minor + 1, 0)
    else:
        upper = Version(0, 0, lower.patch + 1)
    return lambda version, lower=lower, upper=upper: lower <= version < upper


def _tilde(partial: Partial) -> Predicate:
    lower = partial.padded()
    if partial.minor_omitted:
        upper = Version(lower.major + 1, 0, 0)
    else:
        upper = Version(lower.major, lower.minor + 1, 0)
    return lambda version, lower=lower, upper=upper: lower <= version < upper
