"""Domain tests for pin parsing and precedence."""

from __future__ import annotations

import pytest

from app.core.resolver import NoPin, resolve_pin
from app.core.semver import RequestError, parse_installed, parse_request


def installed(*values: str):
    return parse_installed(list(values))


def resolve(**kwargs):
    payload = {"node_version": "", "nvmrc": "", "package_json": "", "installed": installed("20.11.1")}
    payload.update(kwargs)
    return resolve_pin(**payload)


def test_exact_match_selects_that_release():
    result = resolve(node_version="20.11.1", installed=installed("20.11.0", "20.11.1", "20.12.0"))
    assert result.status == "satisfied"
    assert result.matched == "20.11.1"
    assert result.caller_exit_code == 0
    assert result.matches == ("20.11.1",)


def test_major_pin_selects_highest_installed_in_that_major():
    result = resolve(node_version="20", installed=installed("18.20.4", "20.11.1", "20.18.2", "22.14.0"))
    assert result.matched == "20.18.2"
    assert result.matches[0] == "20.18.2"


def test_node_version_beats_nvmrc_and_engines():
    result = resolve(
        node_version="22.14.0",
        nvmrc="lts/*",
        package_json='{"engines":{"node":">=18"}}',
        installed=installed("22.14.0", "24.11.0"),
    )
    assert result.source == "node-version"
    assert result.matched == "22.14.0"
    assert any(".nvmrc" in note for note in result.ignored)
    assert any("engines.node" in note for note in result.ignored)


def test_comment_only_node_version_falls_through_to_nvmrc():
    result = resolve(node_version="# nothing\n\n", nvmrc="22", installed=installed("22.14.0", "22.16.0"))
    assert result.source == "nvmrc"
    assert result.matched == "22.16.0"


def test_missing_install_keeps_caller_exit_zero():
    result = resolve(node_version="20.11.1", nvmrc="18", installed=installed("18.20.4"))
    assert result.status == "missing"
    assert result.matched is None
    assert result.caller_exit_code == 0
    assert "exit code stays 0" in result.explanation


def test_invalid_pin_does_not_fall_through():
    result = resolve(node_version="20.0.0-rc.1", nvmrc="20.11.1", installed=installed("20.11.1"))
    assert result.status == "invalid"
    assert result.source == "node-version"
    assert result.caller_exit_code == 2
    assert result.matched is None
    assert any("fall through" in note for note in result.ignored)


def test_lts_star_uses_snapshot_line_not_newer_current():
    result = resolve(nvmrc="lts/*", installed=installed("22.21.0", "24.11.1", "26.12.0"))
    assert result.matched == "24.11.1"
    assert result.lts_latest_codename == "krypton"
    assert result.lts_latest_major == 24
    assert result.lts_snapshot == "2026-10-14"


def test_lts_star_is_missing_when_that_line_is_absent():
    result = resolve(nvmrc="LTS/*", installed=installed("26.12.0", "22.21.0"))
    assert result.status == "missing"
    assert result.caller_exit_code == 0


def test_lts_codename_and_unknown_codename():
    found = resolve(nvmrc="lts/Iron", installed=installed("18.20.4", "20.18.1", "24.1.0"))
    assert found.matched == "20.18.1"
    unknown = resolve(nvmrc="lts/notaline", installed=installed("20.18.1"))
    assert unknown.status == "invalid"
    assert unknown.caller_exit_code == 2


def test_engines_caret_or_and_boundaries():
    result = resolve(
        package_json='{"name":"eval","engines":{"node":"^18.17.0 || ^22.0.0"}}',
        installed=installed("18.16.0", "18.20.4", "22.14.0", "24.0.0"),
    )
    assert result.source == "engines"
    assert result.matched == "22.14.0"
    bounded = resolve(
        package_json='{"engines":{"node":">=18.0.0 <20"}}',
        installed=installed("18.20.4", "20.0.0", "19.9.0"),
    )
    assert bounded.matched == "19.9.0"


def test_zero_caret_and_tilde_do_not_cross_their_boundary():
    caret = resolve(node_version="^0.10.2", installed=installed("0.10.2", "0.10.48", "0.12.0"))
    assert caret.matched == "0.10.48"
    tilde = resolve(node_version="~0.10.2", installed=installed("0.10.48", "0.11.0"))
    assert tilde.matched == "0.10.48"
    tilde_major = resolve(node_version="~18", installed=installed("18.20.1", "19.0.0"))
    assert tilde_major.matched == "18.20.1"


def test_comparator_padding_and_exact_equals():
    greater = resolve(node_version=">20.0.0", installed=installed("20.0.0", "20.0.1"))
    assert greater.matched == "20.0.1"
    equals = resolve(node_version="=20", installed=installed("20.0.0", "20.0.1"))
    assert equals.matched == "20.0.0"
    spaced = resolve(package_json='{"engines":{"node":">= 18 < 19"}}', installed=installed("18.20.4", "19.0.0"))
    assert spaced.matched == "18.20.4"


def test_malformed_package_json_is_invalid_when_it_is_the_only_pin():
    result = resolve(package_json="{not json", installed=installed("20.11.1"))
    assert result.source == "engines"
    assert result.status == "invalid"
    assert "not valid JSON" in result.explanation


def test_malformed_package_json_is_ignored_when_a_higher_pin_exists():
    result = resolve(node_version="20.11.1", package_json="{", installed=installed("20.11.1"))
    assert result.status == "satisfied"
    assert any("package.json" in note for note in result.ignored)


def test_engines_type_errors_and_absent_engines():
    array = resolve(package_json='["20"]', installed=installed("20.0.0"))
    assert array.status == "invalid"
    bad_engines = resolve(package_json='{"engines":["20"]}', installed=installed("20.0.0"))
    assert bad_engines.status == "invalid"
    blank_node = resolve(package_json='{"engines":{"node":"  "}}', installed=installed("20.0.0"))
    assert blank_node.status == "invalid"
    with pytest.raises(NoPin):
        resolve(package_json='{"name":"tool"}', installed=installed("20.0.0"))


def test_no_pin_and_empty_catalog_alias():
    with pytest.raises(NoPin):
        resolve(installed=[])
    missing = resolve(nvmrc="node", installed=[])
    assert missing.status == "missing"
    assert missing.caller_exit_code == 0


def test_catalog_rejects_partial_blank_and_duplicate_collapses():
    with pytest.raises(RequestError, match="full release"):
        parse_installed(["20"])
    with pytest.raises(RequestError, match="blank"):
        parse_installed(["20.0.0", " "])
    versions = parse_installed(["v20.11.1", "20.11.1", "20.11.0"])
    assert [item.label() for item in versions] == ["20.11.1", "20.11.0"]


def test_rejected_syntax_covers_aliases_wildcards_and_hyphen():
    for text in ("system", "iojs", "current", "unstable", "lts/", "20.x.1", "^18.x", ">=*", "1.2.3 - 1.0.0", "18 - 20", "|| 20", "20 ||"):
        with pytest.raises(RequestError):
            parse_request(text)
    assert parse_request("*").select(installed("1.0.0", "26.1.0"))


def test_full_hyphen_range_is_inclusive():
    result = resolve(node_version="18.20.0 - 20.11.1", installed=installed("18.19.0", "18.20.0", "20.11.1", "20.11.2"))
    assert result.matches == ("20.11.1", "18.20.0")
    assert result.matched == "20.11.1"
