// Labeled fixtures for the smoke-alarm classifier self-test.
// Each test name encodes its expected category: Test..._Expect_<CAT>.
package examples

import (
	"errors"
	"testing"
)

func add(a, b int) int { return a + b }

func TestValueEquality_Expect_S1(t *testing.T) {
	if got := add(2, 3); got != 5 {
		t.Fatalf("got %d", got)
	}
}

func TestErrorCheck_Expect_S2(t *testing.T) {
	err := errors.New("boom")
	if !errors.Is(err, err) {
		t.Fatal("expected match")
	}
}

func TestNoAssertion_Expect_W1(t *testing.T) {
	_ = add(1, 1)
}

func TestNotNil_Expect_W2(t *testing.T) {
	var p *int
	if p == nil {
		_ = p
	}
}
