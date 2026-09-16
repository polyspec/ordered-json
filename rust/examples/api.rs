//! Reports the public API of the crate, one symbol per line, from the source
//! declarations rather than a hand-written list.
use std::fs;

fn main() {
    let source = fs::read_to_string("src/lib.rs").expect("cannot read src/lib.rs");
    let mut symbols: Vec<String> = Vec::new();
    let mut owner: Option<String> = None;
    for line in source.lines() {
        let trimmed = line.trim();
        if let Some(rest) = trimmed.strip_prefix("impl ") {
            // Inherent implementations carry the methods of one public type.
            owner = rest
                .split_whitespace()
                .next()
                .filter(|name| !name.contains('<') && *name != "fmt::Display")
                .map(|name| name.trim_end_matches('{').to_owned());
            continue;
        }
        if trimmed == "}" && line.starts_with('}') {
            owner = None;
            continue;
        }
        let Some(rest) = trimmed.strip_prefix("pub ") else {
            continue;
        };
        let (kind, tail) = match rest.split_once(' ') {
            Some(parts) => parts,
            None => continue,
        };
        if !matches!(kind, "fn" | "struct" | "enum" | "const" | "type" | "trait") {
            continue;
        }
        let name: String = tail
            .chars()
            .take_while(|c| c.is_alphanumeric() || *c == '_')
            .collect();
        if name.is_empty() {
            continue;
        }
        symbols.push(match (&owner, kind) {
            (Some(type_name), "fn") => format!("{type_name}.{name}"),
            _ => name,
        });
    }
    symbols.sort();
    symbols.dedup();
    println!("{}", symbols.join("\n"));
}
