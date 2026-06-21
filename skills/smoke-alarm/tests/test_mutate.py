#!/usr/bin/env python3
"""Self-test for the mutation result parsers.

Runs the cargo-mutants, mutmut, and stryker parsers against real-format tool-output
samples in fixtures/mutation/ and checks the derived survivors and %alarm. Also checks
the zero-dependency XML guard rejects DTD/entity declarations (XXE / billion-laughs).

Run:  python3 tests/test_mutate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "scripts"))

import mutate  # noqa: E402

FIX = ROOT / "fixtures" / "mutation"


def check(name: str, cond: bool, detail: str = "") -> bool:
    print(f"  {'ok' if cond else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not cond else ""))
    return cond


def main() -> int:
    ok = True

    # cargo-mutants: 2 caught, 1 survived, 1 unviable(skipped) -> 66.7% alarm
    cm = mutate.parse_cargo_mutants((FIX / "cargo-mutants-outcomes.json").read_text())
    ok &= check("cargo-mutants caught=2", cm.caught == 2, f"got {cm.caught}")
    ok &= check("cargo-mutants survived=1", cm.survived == 1, f"got {cm.survived}")
    ok &= check("cargo-mutants skipped=1", cm.skipped == 1, f"got {cm.skipped}")
    ok &= check("cargo-mutants pct_alarm~66.7", abs(cm.pct_alarm - 66.7) < 0.5, f"got {cm.pct_alarm}")
    ok &= check("cargo-mutants survivor location", cm.survivors[0].location == "src/lib.rs:25",
                f"got {cm.survivors[0].location}")

    # stryker: Killed+Timeout=2 caught, Survived+NoCoverage=2 survived, CompileError=1
    # skipped -> 50% alarm; survivor locations carry the file:line.
    sk = mutate.parse_stryker_json((FIX / "stryker-mutation.json").read_text())
    ok &= check("stryker caught=2", sk.caught == 2, f"got {sk.caught}")
    ok &= check("stryker survived=2", sk.survived == 2, f"got {sk.survived}")
    ok &= check("stryker skipped=1", sk.skipped == 1, f"got {sk.skipped}")
    ok &= check("stryker pct_alarm~50", abs(sk.pct_alarm - 50.0) < 0.5, f"got {sk.pct_alarm}")
    ok &= check("stryker survivor location", sk.survivors[0].location == "src/math.ts:2",
                f"got {sk.survivors[0].location}")

    # mutmut: 2 caught, 1 survived (failure), 1 skipped (error) -> 66.7% alarm
    mm = mutate.parse_mutmut_junitxml((FIX / "mutmut-junitxml.xml").read_text())
    ok &= check("mutmut caught=2", mm.caught == 2, f"got {mm.caught}")
    ok &= check("mutmut survived=1", mm.survived == 1, f"got {mm.survived}")
    ok &= check("mutmut skipped=1", mm.skipped == 1, f"got {mm.skipped}")
    ok &= check("mutmut pct_alarm~66.7", abs(mm.pct_alarm - 66.7) < 0.5, f"got {mm.pct_alarm}")

    # XML hardening: a DTD/entity payload must be refused by the zero-dep fallback.
    if not mutate._XML_HARDENED:
        billion_laughs = (
            '<?xml version="1.0"?>\n<!DOCTYPE lolz [<!ENTITY lol "lol">]>\n'
            '<testsuites><testsuite><testcase name="&lol;"/></testsuite></testsuites>'
        )
        refused = False
        try:
            mutate.parse_mutmut_junitxml(billion_laughs)
        except ValueError:
            refused = True
        ok &= check("xml guard rejects DTD/entity", refused)
    else:
        print("  ok  defusedxml present — hardened parser in use")

    print("OK — mutation parsers reproduce the sample results" if ok else "FAILURES above")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
