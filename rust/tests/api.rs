//! Package tests for the Rust value API. The shared cases exercise the JSON
//! contract through the adapter; constructor arguments, map building, UTF-16
//! units and wrong-kind access are reachable only from here.
use ordered_json::{parse, parse_bytes, parse_with_max_depth, Kind, OrderedMap, Value, MAX_DEPTH};

#[test]
fn depth_argument_is_bounded() {
    let error = parse_with_max_depth("[]", MAX_DEPTH + 1).unwrap_err();
    assert_eq!(error.message, "max_depth exceeds 256");
    assert_eq!(error.offset, 0);
}

#[test]
fn depth_limit_is_enforced() {
    assert!(parse_with_max_depth("[[1]]", 2).is_ok());
    let shallow = parse_with_max_depth("[[1]]", 1).unwrap_err();
    assert_eq!(shallow.message, "maximum nesting depth exceeded");
}

#[test]
fn bytes_input_is_validated() {
    let error = parse_bytes(b"[\"\xff\"]").unwrap_err();
    assert_eq!(error.message, "invalid UTF-8");
    assert_eq!(error.offset, 2);
    assert_eq!(parse_bytes("[\"\u{d55c}\"]".as_bytes()).unwrap().compact(), "[\"한\"]");
}

#[test]
fn invalid_utf8_reports_the_first_bad_byte() {
    // The bad byte sits at index 2 of ["<bad>"]; the error names that position.
    let error = parse_bytes(b"[\"\xff\"]").unwrap_err();
    assert_eq!(error.message, "invalid UTF-8");
    assert_eq!(error.offset, 2);
}

#[test]
fn parse_errors_report_offsets() {
    let error = parse("[1,]").unwrap_err();
    assert_eq!(error.offset, 3);
    assert_eq!(error.to_string(), "expected JSON value at byte 3");
}

#[test]
fn ordered_map_rejects_non_string_key() {
    let mut members = OrderedMap::new();
    let error = members.insert(Value::number("1").unwrap(), Value::null()).unwrap_err();
    assert_eq!(error.message, "object key must be a string");
    assert!(members.is_empty());
}

#[test]
fn repeated_key_keeps_first_position_and_last_value() {
    let mut members = OrderedMap::new();
    members.insert(Value::string("a"), Value::number("1").unwrap()).unwrap();
    members.insert(Value::string("b"), Value::number("2").unwrap()).unwrap();
    let replaced = members.insert(Value::string("a"), Value::number("3").unwrap()).unwrap();
    assert_eq!(replaced.map(|value| value.compact()), Some("1".to_owned()));
    assert_eq!(members.len(), 2);
    assert_eq!(Value::object(&members).unwrap().compact(), "{\"a\":3,\"b\":2}");
}

#[test]
fn member_lookup_uses_decoded_names() {
    let value = parse("{\"a\\u00e9\":1,\"b\":2}").unwrap();
    assert_eq!(value.get("aé").map(|child| child.compact()), Some("1".to_owned()));
    assert!(value.get("missing").is_none());
    assert_eq!(value.get_units(&[0x62]).map(|child| child.compact()), Some("2".to_owned()));
    assert!(value.get_units(&[0x63]).is_none());
}

#[test]
fn unpaired_surrogate_stays_in_units() {
    let lone = Value::from_units(&[0x61, 0xd800]);
    assert_eq!(lone.compact(), "\"a\\ud800\"");
    assert_eq!(lone.string_units(), Some(&[0x61u16, 0xd800][..]));
    assert_eq!(lone.string_value().unwrap_err().message, "unpaired surrogate; use string_units");
}

#[test]
fn surrogate_pair_decodes() {
    let pair = parse("\"\\ud83c\\udf0d\"").unwrap();
    assert_eq!(pair.string_units(), Some(&[0xd83cu16, 0xdf0d][..]));
    assert_eq!(pair.string_value().unwrap(), "🌍");
}

#[test]
fn factories_validate_arguments() {
    assert_eq!(Value::number(" 1").unwrap_err().message, "expected a number literal without whitespace");
    assert_eq!(Value::number("x").unwrap_err().message, "expected JSON value");
    assert_eq!(Value::array(&[Value::boolean(true), Value::null()]).unwrap().compact(), "[true,null]");
    assert_eq!(Value::string("\"q\"").compact(), "\"\\\"q\\\"\"");
    assert_eq!(Value::object(&OrderedMap::new()).unwrap().compact(), "{}");
}

#[test]
fn wrong_kind_access_is_reported() {
    let array = parse("[1]").unwrap();
    let object = parse("{\"a\":1}").unwrap();
    assert!(array.members().is_none());
    assert!(object.items().is_none());
    assert_eq!(object.number_literal(), None);
    assert_eq!(parse("null").unwrap().boolean_value(), None);
    assert!(parse("1").unwrap().string_units().is_none());
    assert_eq!(array.kind(), Kind::Array);
    assert_eq!(object.kind(), Kind::Object);
}

#[test]
fn root_keeps_surrounding_text() {
    let value = parse("  [1] \n").unwrap();
    assert_eq!(value.raw(), "  [1] \n");
    assert_eq!(value.compact(), "[1]");
    assert_eq!(value.items().unwrap()[0].raw(), "1");
}
