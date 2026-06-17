# Oracle Provenance — where the expected value comes from

This is pillar 3, and it is the one static tools and mutation cannot fully cover.

## The false positive it kills

A test can be green, carry a strong (S1) assertion, and even kill mutants — and still
be wrong, because it asserts what the code **currently does** instead of what it
**should do**. A bug becomes the "expected" value and the test guards it forever.

> Konstantinou, Degiovanni & Papadakis (arXiv:2410.21136): LLM-generated oracles
> frequently encode the *actual* program behaviour rather than the *expected* one,
> turning bugs into passing tests.

The same model that wrote the buggy implementation will happily write a test that
agrees with it. Green then proves *agreement*, not *correctness*.

## The rule

The expected value in an oracle MUST trace to a source independent of the
implementation under test.

### Allowed sources
- A docstring, spec, RFC, or standard ("RFC 8785 says the output is …")
- An issue / acceptance criterion / ticket describing intended behaviour
- A type contract or invariant ("balance is never negative")
- Known mathematics ("`add(2, 3)` is 5 by arithmetic")
- A golden value computed by hand or by an independent reference implementation

### Banned patterns
- **Record-actual:** run the code, copy whatever it returned into the assertion.
- **Auto-snapshot of unreviewed output:** `toMatchSnapshot()` on first run with no human
  check of the recorded value.
- **Expected literal copied from the implementation:** the test's expected value is the
  same literal that appears in the source — the test just mirrors the code.

## How to apply it (when writing a test)

Before writing the assertion, answer in one sentence: *"This SHOULD be X because
<source>."* If the only honest answer is "because that's what the function returns,"
stop — that is smoke. Find the intended behaviour first (read the spec/docstring/issue),
then assert against it.

## How to apply it (when auditing)

Flag any oracle where:
- the expected value equals a literal in the implementation, or
- the test is snapshot-only, or
- the commit that added the test also recorded its expected value from a run.

These are candidates for false-positive B and need a human or a spec to confirm the
expected value is actually correct.
