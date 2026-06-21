#!/usr/bin/env python3
"""smoke-alarm Python AST grader.

The pattern-table grader (grade.py) classifies assertion *text*. For Python that is
needlessly brittle: a regex mis-slices parametrized tests and class methods, and it
calls a helper-based assertion like ``assertValidUser(result)`` a "W1 — no assertion",
which is a factual error that floods real suites.

Python ships a real parser, so for Python we use it. We split units by walking the
module (top-level ``test_*`` functions and ``test_*`` methods of ``Test*`` classes — a
parametrized test is exactly one unit) and classify each by the actual ``Assert`` /
``Call`` nodes in its body. The output is the same UnitVerdict / FileVerdict the rest of
smoke-alarm consumes, so the hook, CLI, and audit are unchanged.

Taxonomy (grade.py docstring), plus one smoke-alarm extension beyond Banik et al. 2026:

    W6  opaque custom assertion — a named helper (assert*/verify*/check*/…) whose body
        we cannot see statically. Weak (so it still flags, fail-closed), but truthful:
        it is NOT "no assertion present". Confirm its strength with mutation (pillar 2).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from grade import STRONG, FileVerdict, UnitVerdict

# Exact unittest assertion method names, grouped by oracle strength.
S1_CALLS = {
    "assertEqual", "assertNotEqual", "assertAlmostEqual", "assertNotAlmostEqual",
    "assertGreater", "assertGreaterEqual", "assertLess", "assertLessEqual",
    "assertListEqual", "assertDictEqual", "assertSetEqual", "assertTupleEqual",
    "assertSequenceEqual", "assertMultiLineEqual", "assertCountEqual", "assertDictContainsSubset",
}
S2_CALLS = {
    "assertIn", "assertNotIn", "assertIsInstance", "assertNotIsInstance",
    "assertRaises", "assertRaisesRegex", "assertRaisesRegexp", "assertWarns",
    "assertWarnsRegex", "assertRegex", "assertRegexpMatches", "assertNotRegex",
    "raises", "warns",  # pytest.raises / pytest.warns context managers
}
W2_CALLS = {"assertIsNone", "assertIsNotNone"}   # existence / non-null only
W3_CALLS = {"assertTrue", "assertFalse"}          # boolean only
MOCK_CALLS = {
    "assert_called", "assert_called_once", "assert_called_with", "assert_called_once_with",
    "assert_any_call", "assert_has_calls", "assert_not_called", "assert_awaited",
    "assert_awaited_once", "assert_awaited_with", "assert_awaited_once_with",
}
CUSTOM_ASSERT_RE = re.compile(r"^(assert|verify|check|expect|ensure|should)", re.IGNORECASE)

# Weak-tier precedence for the single-label verdict. W6 (assertion present, opaque) ranks
# above the genuinely-weaker shapes so an opaque helper never reads as "no assertion".
PRECEDENCE = ["S3", "S2", "S1", "W5", "W4", "W6", "W3", "W2", "W1"]


def _callee_name(call: ast.Call) -> str:
    f = call.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return ""


def _classify_call(call: ast.Call) -> str | None:
    """Return the oracle category a call expresses, or None if it is not an assertion."""
    name = _callee_name(call)
    if not name:
        return None
    if name in W2_CALLS:
        return "W2"
    if name in W3_CALLS:
        return "W3"
    if name in S1_CALLS:
        return "S1"
    if name in S2_CALLS:
        return "S2"
    if "snapshot" in name.lower():
        return "W5"
    if name in MOCK_CALLS or name.startswith("assert_called") or name.startswith("assert_awaited"):
        return "W4"
    if CUSTOM_ASSERT_RE.match(name):
        return "W6"
    return None


def _classify_assert(node: ast.Assert) -> str:
    """An ``assert`` statement: classify by what it actually compares."""
    test = node.test
    if isinstance(test, ast.Compare):
        # syrupy-style snapshot: `assert value == snapshot`
        operands = [test.left, *test.comparators]
        if any(isinstance(o, ast.Name) and o.id == "snapshot" for o in operands):
            return "W5"
        op = test.ops[0]
        if isinstance(op, (ast.In, ast.NotIn)):
            return "S2"
        if isinstance(op, (ast.Is, ast.IsNot)):
            comp = test.comparators[0]
            if isinstance(comp, ast.Constant) and comp.value is None:
                return "W2"          # `x is None` — existence
            return "S1"
        return "S1"                  # ==, !=, <, <=, >, >= — value equality / comparison
    # `assert <anything else>` asserts truthiness -> boolean oracle.
    return "W3"


def _signal_nodes(func: ast.AST):
    """Yield nodes inside ``func`` without descending into nested def/class/lambda, so a
    test's verdict reflects its own body and not a helper closure defined within it."""
    for child in ast.iter_child_nodes(func):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        yield child
        yield from _signal_nodes(child)


def _classify_function(func: ast.AST, name: str) -> UnitVerdict:
    cats: list[str] = []
    matched: list[str] = []
    for node in _signal_nodes(func):
        cat = None
        if isinstance(node, ast.Assert):
            cat = _classify_assert(node)
            label = "assert-stmt"
        elif isinstance(node, ast.Call):
            cat = _classify_call(node)
            label = _callee_name(node)
        if cat:
            cats.append(cat)
            matched.append(f"{cat}:{label}")

    distinct_strong = {c for c in cats if c in STRONG}
    if len(distinct_strong) >= 2:
        category = "S3"
    else:
        category = next((c for c in PRECEDENCE if c in cats), "W1")
    tier = "strong" if category in STRONG else "weak"
    return UnitVerdict(name=name, category=category, tier=tier, matched=matched)


def _is_test_func(node: ast.AST) -> bool:
    return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test")


def _looks_like_test_class(cls: ast.ClassDef) -> bool:
    if cls.name.startswith("Test"):
        return True
    for base in cls.bases:
        if isinstance(base, ast.Name) and "TestCase" in base.id:
            return True
        if isinstance(base, ast.Attribute) and "TestCase" in base.attr:
            return True
    return False


def grade_python_source(source: str, path: str = "<source>") -> FileVerdict:
    """Grade Python test source via AST. Falls back to no units on a syntax error
    (caller decides what an ungradeable file means; the hook treats it as fail-closed)."""
    tree = ast.parse(source)
    units: list[UnitVerdict] = []
    for node in tree.body:
        if _is_test_func(node):
            units.append(_classify_function(node, node.name))
        elif isinstance(node, ast.ClassDef) and _looks_like_test_class(node):
            for item in node.body:
                if _is_test_func(item):
                    units.append(_classify_function(item, item.name))
    return FileVerdict(path=path, lang="python", units=units)


def grade_python_file(path: Path) -> FileVerdict:
    source = path.read_text(encoding="utf-8", errors="replace")
    return grade_python_source(source, str(path))
