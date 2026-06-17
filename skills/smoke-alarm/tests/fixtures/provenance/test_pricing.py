# Provenance fixtures for the smoke-alarm scanner self-test.
# Each test name encodes the expected heuristic flag:
#   ..._flag_<KIND>   -> that flag must fire
#   ..._noflag        -> no flag should fire

DISCOUNT_RATE = 0.2  # an implementation literal


def price_after_discount(p):
    return p * (1 - DISCOUNT_RATE)


def compute():
    return price_after_discount(100)


def render():
    return {"price": compute()}


def test_grounded_in_intent_noflag():
    # Spec: a $100 item at 20% off is $80. Expected value comes from the spec.
    assert price_after_discount(100) == 80.0


def test_copied_from_impl_flag_LITERAL_IN_IMPL():
    # Contrived: the expected value is the implementation's own constant.
    assert price_after_discount(50) == 0.2


def test_snapshot_only_flag_SNAPSHOT():
    assert render() == snapshot  # noqa: F821 - syrupy-style fixture


def test_two_runs_flag_SELF_COMPARE():
    a = compute()
    b = compute()
    assert a == b


def test_recorded_output_flag_RECORD_ACTUAL():
    # matches the current output
    assert compute() == 73.5
