// Adapter only. The shared Python verifier owns examples and expectations.
use ordered_json::{parse_bytes, Kind, Member, Value};
use std::{
    fs,
    io::{self, BufRead},
};

fn quote(s: &str) -> String {
    Value::string(s).raw().to_owned()
}
fn text(v: &Value) -> String {
    Value::from_units(v.string_units().unwrap())
        .raw()
        .to_owned()
}
fn tree(v: &Value) -> String {
    match v.kind() {
        Kind::Object => format!(
            "[\"object\",[{}]]",
            v.members()
                .unwrap()
                .iter()
                .map(|m| format!("[{},{}]", text(&m.key), tree(&m.value)))
                .collect::<Vec<_>>()
                .join(",")
        ),
        Kind::Array => format!(
            "[\"array\",[{}]]",
            v.items()
                .unwrap()
                .iter()
                .map(tree)
                .collect::<Vec<_>>()
                .join(",")
        ),
        Kind::String => format!("[\"string\",{}]", text(v)),
        Kind::Number => format!("[\"number\",{}]", quote(v.number_literal().unwrap())),
        Kind::Boolean => format!("[\"boolean\",{}]", v.boolean_value().unwrap()),
        Kind::Null => "[\"null\"]".into(),
    }
}
fn rebuild(v: &Value) -> Value {
    match v.kind() {
        Kind::Object => Value::object(
            &v.members()
                .unwrap()
                .iter()
                .map(|m| Member {
                    key: m.key.clone(),
                    value: rebuild(&m.value),
                })
                .collect::<Vec<_>>(),
        )
        .unwrap(),
        Kind::Array => {
            Value::array(&v.items().unwrap().iter().map(rebuild).collect::<Vec<_>>()).unwrap()
        }
        _ => v.clone(),
    }
}
fn main() {
    for line in io::stdin().lock().lines() {
        let bytes = fs::read(line.unwrap()).expect("cannot read document");
        match parse_bytes(&bytes) {
            Err(_) => println!("{{\"ok\":false}}"),
            Ok(v) => println!(
                "{{\"ok\":true,\"raw\":{},\"compact\":{},\"tree\":{},\"rebuilt\":{}}}",
                quote(v.raw()),
                quote(&v.compact()),
                tree(&v),
                quote(&rebuild(&v).compact())
            ),
        }
    }
}
