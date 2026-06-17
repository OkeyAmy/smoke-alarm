#!/usr/bin/env python3
"""Self-test for the smoke-alarm classifier.

Every fixture file holds real test units whose names encode the expected category
(..._expect_<CAT> in Python/TS, ..._Expect_<CAT> in Go, ..._expect_<cat> in Rust).
The classifier must reproduce each label. This is the reproducible benchmark
referenced in the design spec — it grounds the κ/agreement claim in real inputs,
not hardcoded values.

Run:  python3 tests/test_grade.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "scripts"))

import grade  # noqa: E402

LABEL_RE = re.compile(r"expect[_-]([sw][123])", re.IGNORECASE)


def expected_category(unit_name: str) -> str | None:
    m = LABEL_RE.search(unit_name)
    return m.group(1).upper() if m else None


def main() -> int:
    fixtures = sorted((ROOT / "fixtures").rglob("*"))
    fixtures = [p for p in fixtures if p.is_file() and p.suffix.lower() in grade.EXT_TO_LANG]
    if not fixtures:
        print("no fixtures found", file=sys.stderr)
        return 2

    total = passed = 0
    failures: list[str] = []
    for fx in fixtures:
        fv = grade.grade_file(fx)
        if fv is None:
            continue
        for unit in fv.units:
            want = expected_category(unit.name)
            if want is None:
                continue
            total += 1
            if unit.category == want:
                passed += 1
            else:
                failures.append(
                    f"{fx.name}::{unit.name}  expected {want}  got {unit.category}"
                )

    print(f"{passed}/{total} labeled units classified correctly")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("OK — classifier reproduces all fixture labels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
