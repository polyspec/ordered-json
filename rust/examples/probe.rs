// Adapter only. The shared Python verifier owns examples and expectations.
use ordered_json::{parse_bytes, stringify, Kind, OrderedMap, Value};
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
                .map(|(key, value)| format!("[{},{}]", text(key), tree(value)))
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
        Kind::Object => {
            let mut members = OrderedMap::new();
            for (key, _) in v.members().unwrap().iter() {
                members.insert(key.clone(), Value::null()).unwrap();
            }
            for (key, _) in v.members().unwrap().iter().rev() {
                members
                    .insert(
                        key.clone(),
                        rebuild(v.get_units(key.string_units().unwrap()).unwrap()),
                    )
                    .unwrap();
            }
            Value::object(&members).unwrap()
        }
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
                "{{\"ok\":true,\"raw\":{},\"serialized\":{},\"compact\":{},\"tree\":{},\"rebuilt\":{}}}",
                quote(v.raw()),
                quote(&stringify(&v)),
                quote(&v.compact()),
                tree(&v),
                quote(&rebuild(&v).compact())
            ),
        }
    }
}
