// Labeled fixtures for the smoke-alarm classifier self-test.
// Each test fn name encodes its expected category: ..._expect_<cat>.

fn add(a: i32, b: i32) -> i32 {
    a + b
}

fn parse(s: &str) -> Result<i32, std::num::ParseIntError> {
    s.parse::<i32>()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn value_equality_expect_s1() {
        assert_eq!(add(2, 3), 5);
    }

    #[test]
    fn error_check_expect_s2() {
        assert!(parse("xx").is_err());
    }

    #[test]
    fn strong_combo_expect_s3() {
        assert_eq!(add(2, 2), 4);
        assert!(parse("nope").is_err());
    }

    #[test]
    fn no_assertion_expect_w1() {
        let _ = add(1, 1);
    }

    #[test]
    fn some_only_expect_w2() {
        assert!(Some(add(1, 1)).is_some());
    }
}
