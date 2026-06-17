# Mutation tooling per language

`mutate.py` (pillar 2) wraps these. Install the one for your stack. Without it,
smoke-alarm falls back to static + provenance and refuses to certify a test as a
proven alarm (fail-closed).

| Language | Tool | Install | Notes |
|----------|------|---------|-------|
| Rust | [cargo-mutants](https://github.com/sourcefrog/cargo-mutants) | `cargo install cargo-mutants` | Run in the crate root |
| Python | [mutmut](https://github.com/boxed/mutmut) | `pip install mutmut` | Configure `paths_to_mutate` in `setup.cfg`/`pyproject.toml` |
| TypeScript/JS | [Stryker](https://stryker-mutator.io/) | `pnpm add -D @stryker-mutator/core` | Needs `stryker.conf.json`; supports Jest/Vitest |
| Go | [gremlins](https://github.com/go-gremlins/gremlins) | `go install github.com/go-gremlins/gremlins/cmd/gremlins@latest` | Run `gremlins unleash ./...` |

## How to read the result

- **Mutant killed** = some test failed when the code was broken → the oracle works.
- **Mutant survived** = the code was broken and every test still passed → those tests
  are smoke. Find the test that should have covered that line and strengthen its
  oracle.

## Why mutation, not coverage

Coverage tells you a line *executed*; it says nothing about whether the result was
*checked*. Coverage correlates only weakly with fault detection (Inozemtseva & Holmes,
ICSE 2014); mature suites show gaps up to 51% between executed and checked code
(Hossain et al., ICSE 2023). Mutation measures the thing that matters: does a bug make
a test fail.

## Why mutation still is not enough

Mutation cannot catch false-positive B: a test that asserts the *wrong* expected value
can still kill mutants. That is what pillar 3 (`references/provenance.md`) is for.
