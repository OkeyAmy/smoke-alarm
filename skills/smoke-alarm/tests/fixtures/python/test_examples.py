# Labeled fixtures for the smoke-alarm classifier self-test.
# Each test function name encodes its EXPECTED category: ..._expect_<CAT>.
# These are real test functions, not strings — the classifier reads this file.


def add(a, b):
    return a + b


def test_value_equality_expect_S1():
    assert add(2, 3) == 5


def test_error_check_expect_S2():
    import pytest
    with pytest.raises(ZeroDivisionError):
        _ = 1 / 0


def test_strong_combo_expect_S3():
    import pytest
    assert add(2, 2) == 4
    with pytest.raises(TypeError):
        add(1, None)


def test_no_assertion_expect_W1():
    result = add(1, 1)
    print(result)  # executes, verifies nothing


def test_not_none_expect_W2():
    result = add(1, 1)
    assert result is not None


def test_boolean_only_expect_W3():
    ok = bool(add(1, 1))
    assert ok
