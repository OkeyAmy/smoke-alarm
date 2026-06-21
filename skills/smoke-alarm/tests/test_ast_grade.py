#!/usr/bin/env python3
"""Real-input tests for the Python AST grader.

Each case is genuine Python source parsed and graded by the actual code path
(grade_python_source -> ast.parse -> classify). Several cases are exactly the ones the
old regex grader got wrong; they are here to prove the AST grader fixes them, not to
re-assert a hardcoded answer.

Run:  python3 tests/test_ast_grade.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from ast_grade import grade_python_source  # noqa: E402

# name -> (source, expected_category). The function name documents the case.
CASES: dict[str, tuple[str, str]] = {
    # --- the flagship regex failures the AST grader must fix ---
    "helper_assert_is_not_W1": (
        "def test_user():\n"
        "    result = build_user()\n"
        "    assertValidUser(result)\n",
        "W6",  # regex called this W1 'no assertion'; it IS an assertion, just opaque
    ),
    "value_equality": (
        "def test_sum():\n"
        "    assert add(2, 3) == 5\n",
        "S1",
    ),
    # --- weak shapes, correctly identified ---
    "no_assertion": (
        "def test_runs():\n"
        "    do_thing()\n",
        "W1",
    ),
    "existence_only": (
        "def test_exists():\n"
        "    assert build() is not None\n",
        "W2",
    ),
    "boolean_only": (
        "def test_flag():\n"
        "    assert is_ready()\n",
        "W3",
    ),
    "mock_only": (
        "def test_called():\n"
        "    svc = Mock()\n"
        "    run(svc)\n"
        "    svc.save.assert_called_once()\n",
        "W4",
    ),
    "snapshot_only": (
        "def test_snap(snapshot):\n"
        "    assert render() == snapshot\n",
        "W5",
    ),
    # --- strong shapes ---
    "containment": (
        "def test_in():\n"
        "    assert 'x' in result()\n",
        "S2",
    ),
    "type_check": (
        "class TestThing:\n"
        "    def test_type(self):\n"
        "        self.assertIsInstance(make(), Thing)\n",
        "S2",
    ),
    "raises_contextmanager": (
        "def test_raises():\n"
        "    with pytest.raises(ValueError):\n"
        "        parse('bad')\n",
        "S2",
    ),
    "two_strong_is_S3": (
        "def test_both():\n"
        "    assert compute() == 42\n"
        "    assert 'ok' in status()\n",
        "S3",
    ),
}


def main() -> int:
    passed = total = 0
    failures: list[str] = []

    for name, (source, want) in CASES.items():
        total += 1
        fv = grade_python_source(source)
        got = fv.units[0].category if fv.units else "<no-units>"
        if got == want:
            passed += 1
        else:
            failures.append(f"{name}: want {want}, got {got}")

    # parametrized test is ONE unit (the regex grader's unit splitting could not be
    # trusted here); the decorator must not change unit count or the verdict.
    total += 1
    param_src = (
        "@pytest.mark.parametrize('a,b,c', [(1, 2, 3), (2, 2, 4)])\n"
        "def test_add(a, b, c):\n"
        "    assert add(a, b) == c\n"
    )
    fv = grade_python_source(param_src)
    if len(fv.units) == 1 and fv.units[0].category == "S1":
        passed += 1
    else:
        failures.append(f"parametrized: want 1 unit S1, got {len(fv.units)} units "
                        f"{[u.category for u in fv.units]}")

    # multiple test methods in a TestCase subclass are each their own unit.
    total += 1
    cls_src = (
        "class TestMath(unittest.TestCase):\n"
        "    def test_a(self):\n"
        "        self.assertEqual(add(1, 1), 2)\n"
        "    def test_b(self):\n"
        "        self.assertTrue(is_even(2))\n"
        "    def helper(self):\n"        # not a test method -> not a unit
        "        return 1\n"
    )
    fv = grade_python_source(cls_src)
    names = sorted(u.name for u in fv.units)
    if names == ["test_a", "test_b"]:
        passed += 1
    else:
        failures.append(f"class methods: want [test_a, test_b], got {names}")

    print(f"{passed}/{total} checks passed")
    for f in failures:
        print(f"  - {f}")
    if not failures:
        print("OK — AST grader classifies real Python correctly (incl. former regex misses)")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
