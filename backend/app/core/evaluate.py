"""Score the resolver against the hand-labeled toolchain pin cases."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.resolver import Resolution, resolve_pin
from app.core.semver import RequestError, parse_installed

CASES_PATH = Path(__file__).resolve().parents[1] / "data" / "pin_cases.json"


def load_cases(path: Path | None = None) -> list[dict]:
    document = json.loads((path or CASES_PATH).read_text(encoding="utf-8"))
    cases = document["cases"]
    if not isinstance(cases, list) or not cases:
        raise ValueError("Pin case file has no cases.")
    return cases


def score(cases: list[dict] | None = None) -> dict:
    rows = cases if cases is not None else load_cases()
    failures: list[dict] = []
    source_hits = 0
    status_hits = 0
    match_hits = 0
    exit_hits = 0
    for case in rows:
        try:
            result = run_case(case)
        except (RequestError, ValueError) as exc:
            failures.append({"id": case.get("id"), "error": str(exc)})
            continue
        ok = True
        if result.source != case["expect_source"]:
            ok = False
        else:
            source_hits += 1
        if result.status != case["expect_status"]:
            ok = False
        else:
            status_hits += 1
        if result.matched != case["expect_matched"]:
            ok = False
        else:
            match_hits += 1
        if result.caller_exit_code != case["expect_exit"]:
            ok = False
        else:
            exit_hits += 1
        if not ok:
            failures.append(
                {
                    "id": case["id"],
                    "source": result.source,
                    "status": result.status,
                    "matched": result.matched,
                    "caller_exit_code": result.caller_exit_code,
                    "explanation": result.explanation,
                }
            )
    total = len(rows)
    return {
        "cases": total,
        "passed": total - len(failures),
        "source_agreement": f"{source_hits}/{total}",
        "status_agreement": f"{status_hits}/{total}",
        "match_agreement": f"{match_hits}/{total}",
        "exit_agreement": f"{exit_hits}/{total}",
        "failures": failures,
    }


def run_case(case: dict) -> Resolution:
    package = case.get("package_json", "")
    if isinstance(package, dict):
        package_text = json.dumps(package)
    else:
        package_text = package or ""
    catalog = parse_installed(list(case.get("installed", [])))
    return resolve_pin(
        node_version=case.get("node_version") or "",
        nvmrc=case.get("nvmrc") or "",
        package_json=package_text,
        installed=catalog,
    )


def main() -> int:
    report = score()
    print(f"cases {report['cases']}")
    print(f"passed {report['passed']}")
    print(f"source_agreement {report['source_agreement']}")
    print(f"status_agreement {report['status_agreement']}")
    print(f"match_agreement {report['match_agreement']}")
    print(f"exit_agreement {report['exit_agreement']}")
    if report["failures"]:
        print("failures")
        for item in report["failures"]:
            print(json.dumps(item, sort_keys=True))
        return 1
    print("failures none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
