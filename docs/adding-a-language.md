# Adding a language

Adding a language is **data-only** — a pattern table and fixtures. No Python changes.
This walks through adding **Ruby** (RSpec/Minitest) as a worked example.

## 1. Register the file extension

`grade.py` and `mutate.py` share an `EXT_TO_LANG` map. Add your extension:

```python
# scripts/grade.py  (and scripts/mutate.py)
EXT_TO_LANG = {
    ...
    ".rb": "ruby",
}
```

This is the one code touch — wiring an extension to a language name. Everything else is
data.

## 2. Write the pattern table

Create `scripts/patterns/ruby.toml`. Group assertion regex by taxonomy category. Order
does not matter; the classifier takes the highest signal (S3 > S2 > S1 > W5 … > W1).

```toml
lang = "ruby"

# How to find the start of a test unit.
unit_pattern = '^\s*(?:it|specify|test|def test_)\b.*'

[signals.S1]
desc = "value equality or comparison"
patterns = [
  'expect\([^)]*\)\.to\s+eq\b', 'assert_equal\b', 'expect\([^)]*\)\.to\s+(?:be|eql)\b',
]

[signals.S2]
desc = "error, containment, or type checks"
patterns = [
  'expect\s*\{[^}]*\}\.to\s+raise_error', 'assert_raises\b',
  'expect\([^)]*\)\.to\s+include\b', 'assert_includes\b',
]

[signals.W2]
desc = "existence / non-null checks only"
patterns = ['expect\([^)]*\)\.to\s+be_nil', 'expect\([^)]*\)\.not_to\s+be_nil']

[signals.W3]
desc = "boolean asserts only (no value compared)"
patterns = ['expect\([^)]*\)\.to\s+be(?:_truthy|_falsey)?\b', 'assert\b']

[signals.W4]
desc = "mock / call-verification only"
patterns = ['expect\([^)]*\)\.to\s+have_received\b', 'have_received\b']

[signals.W5]
desc = "snapshot match only"
patterns = ['match_snapshot\b']
```

Notes:
- `unit_pattern` must capture a group for the unit name when natural; if it has no
  group, the whole match is used as the name.
- `unit_guard` is optional — use it when a unit only counts if a marker precedes it
  (Rust uses `#\[test\]`). RSpec needs none.
- A unit matching no pattern is **W1** (no oracle) — that is the fail-closed default.

## 3. Add labeled fixtures

Create `tests/fixtures/ruby/example_spec.rb` with real test units whose names encode
the expected category (`..._expect_<CAT>`), one per category you support:

```ruby
# expected category encoded in each example name
RSpec.describe "add" do
  it "value equality expect_S1" do
    expect(add(2, 3)).to eq(5)
  end

  it "error check expect_S2" do
    expect { boom }.to raise_error(RuntimeError)
  end

  it "no assertion expect_W1" do
    add(1, 1)
  end
end
```

## 4. Run the self-test

`tests/test_grade.py` discovers any fixture under `tests/fixtures/` and checks the
classifier reproduces every `expect_<CAT>` label — your new language included:

```bash
python3 skills/smoke-alarm/tests/test_grade.py
```

If a label fails, tighten the regex in your TOML (a common cause: a strong pattern is
too greedy and swallows a weak case, or `$`/boundaries behave differently than you
expect — signal patterns are matched multiline).

## 5. (Optional) wire mutation

To support pillar 2 for the language, add a `Backend` entry in `scripts/mutate.py`
(tool name, version-check command, run command, install hint) and, ideally, a parser
for its result artifact plus a sample-output fixture under `tests/fixtures/mutation/`.

That is the whole process: one extension line, one TOML, a fixture file, green
self-test.
