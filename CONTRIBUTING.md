# Contributing to smoke-alarm

Thanks for helping make agent-written tests actually verify behaviour.

## Principles

- **The skill is the product.** `SKILL.md` is the personality an agent adopts; the
  scripts are the instruments that personality uses. Changes should keep both honest.
- **Fail closed.** If a check cannot run or an assertion is unrecognized, treat the
  test as unproven (smoke), never silently pass it.
- **No overclaiming.** Don't describe a capability the code doesn't have. If something
  is a heuristic, say so. If accuracy is unmeasured, say so.
- **Tests use real inputs.** Fixtures are real test files / real tool output, not
  hardcoded return values. A test that asserts a mock was called is exactly what this
  project flags — don't write one.

## Dev setup

No build step. You need Python ≥ 3.11.

```bash
git clone https://github.com/OkeyAmy/smoke-alarm
cd smoke-alarm
python3 skills/smoke-alarm/tests/test_grade.py
python3 skills/smoke-alarm/tests/test_provenance.py
python3 skills/smoke-alarm/tests/test_mutate.py
```

All three must pass before you open a PR. CI runs them on Python 3.11–3.13.

## Common contributions

- **Add a language:** see [docs/adding-a-language.md](docs/adding-a-language.md). Pattern
  table + fixtures, one extension line. Include fixtures for every category you claim.
- **Improve patterns for an existing language:** edit `scripts/patterns/<lang>.toml`,
  add a fixture that would have been misclassified before, confirm the self-test catches
  it.
- **Add a mutation backend parser:** add the `Backend` entry and a parser in
  `scripts/mutate.py`, plus a real sample-output fixture under
  `tests/fixtures/mutation/` and a case in `tests/test_mutate.py`.
- **Reduce a false positive/negative:** add the offending case as a fixture first
  (red), then fix.

## PR checklist

- [ ] Self-tests pass on your machine
- [ ] New behaviour has a fixture exercising real input
- [ ] Docs updated if behaviour or flags changed
- [ ] No new claim that the code can't back up
- [ ] `CHANGELOG.md` has an entry under "Unreleased"

## Reporting bugs

Open an issue with the smallest test file that reproduces the misclassification, the
command you ran, and what you expected vs. what you got.
