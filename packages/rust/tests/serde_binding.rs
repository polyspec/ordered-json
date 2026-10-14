use polyspec_ordered_json::serde::{from_slice, from_str, to_string};
use polyspec_ordered_json::{parse, Value};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, PartialEq, Serialize, Deserialize)]
struct Wire {
    service: u64,
    uuids: Vec<String>,
}
#[derive(Debug, PartialEq, Serialize, Deserialize)]
struct View {
    name: String,
    pattern: String,
    side: String,
    #[serde(skip_serializing_if = "Option::is_none", default)]
    component: Option<String>,
}
#[derive(Debug, PartialEq, Serialize, Deserialize)]
struct Theme {
    id: String,
    name: String,
}
#[derive(Debug, PartialEq, Serialize, Deserialize)]
struct Manifest {
    id: String,
    name: String,
    version: String,
    #[serde(rename = "runtimeDependencies")]
    runtime_dependencies: BTreeMap<String, String>,
    provides: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none", default)]
    identity: Option<String>,
    views: Vec<View>,
    widgets: Vec<String>,
    themes: Vec<Theme>,
    forms: Vec<String>,
    commands: Vec<String>,
}

#[test]
fn serde_wire_bytes_and_round_trip() {
    let value = Wire {
        service: 9007199254740993,
        uuids: vec!["한 서비스".into()],
    };
    let fixture = include_str!("fixtures/wire.json");
    let encoded = to_string(&value).unwrap();
    assert_eq!(encoded.as_bytes(), fixture.as_bytes());
    assert_eq!(from_str::<Wire>(&encoded).unwrap(), value);
}
#[test]
fn serde_manifest_bytes_and_round_trip() {
    let value = Manifest {
        id: "board".into(),
        name: "Board".into(),
        version: "0.1.0".into(),
        runtime_dependencies: BTreeMap::new(),
        provides: vec![],
        identity: None,
        views: vec![View {
            name: "list".into(),
            pattern: "/".into(),
            side: "front".into(),
            component: None,
        }],
        widgets: vec![],
        themes: vec![Theme {
            id: "default".into(),
            name: "Default".into(),
        }],
        forms: vec![],
        commands: vec![],
    };
    let fixture = include_bytes!("fixtures/manifest.json");
    let encoded = to_string(&value).unwrap();
    assert_eq!(encoded.as_bytes(), fixture);
    assert_eq!(from_slice::<Manifest>(fixture).unwrap(), value);
}
#[test]
fn serde_rejects_invalid_and_unconsumed_input() {
    for input in [
        b"{\"service\":1,\"service\":2,\"uuids\":[]}".as_slice(),
        b"{\"service\":1,\"uuids\":[],\"extra\":1}",
        b"{\"service\":\"1\",\"uuids\":[]}",
        b"{\"service\":1,\"uuids\":[]} trailing",
        b"{\"service\":1,\"uuids\":[\"\xff\"]}",
    ] {
        assert!(from_slice::<Wire>(input).is_err());
    }
    assert!(to_string(&f64::NAN).is_err());
    assert!(to_string(&f64::INFINITY).is_err());
    assert_eq!(to_string(&0.1_f32).unwrap(), "0.1");
    assert_eq!(to_string(&u128::MAX).unwrap(), u128::MAX.to_string());
    assert_eq!(to_string(&i128::MIN).unwrap(), i128::MIN.to_string());
    assert!(to_string(&BTreeMap::from([(1, "value")])).is_err());
}
#[test]
fn serde_rejects_duplicate_struct_fields() {
    struct Repeated;
    impl Serialize for Repeated {
        fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
            use serde::ser::SerializeStruct;
            let mut fields = serializer.serialize_struct("Repeated", 2)?;
            fields.serialize_field("id", &1)?;
            fields.serialize_field("id", &2)?;
            fields.end()
        }
    }
    assert!(to_string(&Repeated).is_err());
}

#[derive(Debug, Serialize, Deserialize)]
struct RawWire {
    call: String,
    props: Option<Value>,
    keys: Value,
}

#[test]
fn serde_embedded_values_preserve_order_and_number_tokens() {
    let raw = r#"{"z":123456789012345678901234567890.123456789,"a":[{"b":2,"a":"한"}]}"#;
    let value = RawWire {
        call: "view".into(),
        props: Some(parse(raw).unwrap()),
        keys: parse(r#"{"second":2,"first":1}"#).unwrap(),
    };
    let expected = format!(r#"{{"call":"view","props":{raw},"keys":{{"second":2,"first":1}}}}"#);
    assert_eq!(to_string(&value).unwrap(), expected);
    let decoded: RawWire = from_str(&expected).unwrap();
    assert_eq!(decoded.props.unwrap().compact(), raw);
    assert_eq!(decoded.keys.compact(), r#"{"second":2,"first":1}"#);
    assert_eq!(
        serde_json::to_string(&value.keys).unwrap(),
        r#"{"second":2,"first":1}"#
    );
    assert!(from_str::<RawWire>(r#"{"call":"view","props":{"x":1,"x":2},"keys":{}}"#).is_err());
}

#[test]
fn serde_value_respects_container_depth() {
    let text = format!("{}0{}", "[".repeat(256), "]".repeat(256));
    let value = parse(&text).unwrap();
    assert_eq!(to_string(&value).unwrap(), text);
    let decoded: Value = from_str(&text).unwrap();
    assert_eq!(decoded.compact(), text);
    assert!(from_str::<Value>(&format!("[{}]", text)).is_err());
}

#[test]
fn serde_value_preserves_unpaired_surrogate_token() {
    let value = Value::from_units(&[0xd800]);
    assert_eq!(to_string(&value).unwrap(), r#""\ud800""#);
    assert_eq!(
        from_str::<Value>(r#""\ud800""#).unwrap().string_units(),
        Some(&[0xd800][..])
    );
}
