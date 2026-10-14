"""The labeled toolchain set is the reproducible baseline for this resolver."""

from __future__ import annotations

from app.core.evaluate import load_cases, score


def test_labeled_pin_cases_match_the_resolver():
    report = score()
    assert report["failures"] == []
    assert report["cases"] == len(load_cases())
    assert report["passed"] == report["cases"]
    assert report["cases"] >= 8


def test_score_reports_a_disagreement_without_hiding_it():
    case = {
        "id": "forced-mismatch",
        "node_version": "20.0.0",
        "installed": ["20.0.0"],
        "expect_source": "nvmrc",
        "expect_status": "missing",
        "expect_matched": "1.0.0",
        "expect_exit": 2,
    }
    report = score([case])
    assert report["passed"] == 0
    assert report["failures"][0]["id"] == "forced-mismatch"
    assert report["failures"][0]["status"] == "satisfied"
