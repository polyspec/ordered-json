//! Ordered, immutable JSON values. See [`parse`] and [`Value`].
use std::{collections::HashMap, fmt, sync::Arc};

pub const MAX_DEPTH: usize = 256;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Error {
    /// Byte offset into the UTF-8 input (zero for API/type errors).
    pub offset: usize,
    pub message: &'static str,
}
impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{} at byte {}", self.message, self.offset)
    }
}
impl std::error::Error for Error {}
type Result<T> = std::result::Result<T, Error>;
fn error(message: &'static str) -> Error {
    Error { offset: 0, message }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Kind {
    Object,
    Array,
    String,
    Number,
    Boolean,
    Null,
}

/// An associative map that keeps each key's first insertion position.
#[derive(Debug, Clone, Default)]
pub struct OrderedMap {
    keys: Vec<Value>,
    values: HashMap<Vec<u16>, Value>,
}
impl OrderedMap {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn insert(&mut self, key: Value, value: Value) -> Result<Option<Value>> {
        if key.kind != Kind::String {
            return Err(error("object key must be a string"));
        }
        if !self.values.contains_key(&key.units) {
            self.keys.push(key.clone());
        }
        Ok(self.values.insert(key.units, value))
    }
    pub fn get(&self, key: &str) -> Option<&Value> {
        self.get_units(&key.encode_utf16().collect::<Vec<_>>())
    }
    pub fn get_units(&self, key: &[u16]) -> Option<&Value> {
        self.values.get(key)
    }
    pub fn iter(&self) -> impl DoubleEndedIterator<Item = (&Value, &Value)> {
        self.keys.iter().map(|key| (key, &self.values[&key.units]))
    }
    pub fn len(&self) -> usize {
        self.values.len()
    }
    pub fn is_empty(&self) -> bool {
        self.values.is_empty()
    }
}

#[derive(Debug, Clone)]
pub struct Value {
    source: Arc<str>,
    start: usize,
    end: usize,
    kind: Kind,
    members: OrderedMap,
    items: Vec<Value>,
    units: Vec<u16>,
}

impl Value {
    pub fn kind(&self) -> Kind {
        self.kind
    }
    pub fn raw(&self) -> &str {
        &self.source[self.start..self.end]
    }
    pub fn members(&self) -> Option<&OrderedMap> {
        (self.kind == Kind::Object).then_some(&self.members)
    }
    pub fn items(&self) -> Option<&[Value]> {
        (self.kind == Kind::Array).then_some(&self.items)
    }
    /// UTF-16 code units also represent escaped, unpaired surrogates losslessly.
    pub fn string_units(&self) -> Option<&[u16]> {
        (self.kind == Kind::String).then_some(&self.units)
    }
    pub fn string_value(&self) -> Result<String> {
        let units = self
            .string_units()
            .ok_or_else(|| error("expected string"))?;
        String::from_utf16(units).map_err(|_| error("unpaired surrogate; use string_units"))
    }
    pub fn number_literal(&self) -> Option<&str> {
        (self.kind == Kind::Number).then(|| self.raw().trim())
    }
    pub fn boolean_value(&self) -> Option<bool> {
        (self.kind == Kind::Boolean).then(|| self.raw().trim() == "true")
    }
    pub fn get(&self, key: &str) -> Option<&Value> {
        self.members.get(key)
    }
    pub fn get_units(&self, key: &[u16]) -> Option<&Value> {
        self.members.get_units(key)
    }
    pub fn string(text: &str) -> Self {
        Self::from_units(&text.encode_utf16().collect::<Vec<_>>())
    }
    /// Construct a JSON string without replacing unpaired surrogates.
    pub fn from_units(units: &[u16]) -> Self {
        use std::fmt::Write;
        let mut out = String::from("\"");
        for &unit in units {
            if (0x20..=0x7e).contains(&unit) && unit != 34 && unit != 92 {
                out.push(char::from_u32(unit as u32).unwrap());
            } else {
                write!(out, "\\u{unit:04x}").unwrap();
            }
        }
        out.push('"');
        parse(&out).expect("encoded string is valid JSON")
    }
    pub fn number(literal: &str) -> Result<Self> {
        let value = parse(literal)?;
        if value.kind != Kind::Number || literal.trim() != literal {
            return Err(error("expected a number literal without whitespace"));
        }
        Ok(value)
    }
    pub fn boolean(value: bool) -> Self {
        parse(if value { "true" } else { "false" }).unwrap()
    }
    pub fn null() -> Self {
        parse("null").unwrap()
    }
    pub fn array(items: &[Value]) -> Result<Self> {
        parse(&format!(
            "[{}]",
            items
                .iter()
                .map(Self::compact)
                .collect::<Vec<_>>()
                .join(",")
        ))
    }
    pub fn object(members: &OrderedMap) -> Result<Self> {
        let mut parts = Vec::with_capacity(members.len());
        for (key, value) in members.iter() {
            parts.push(format!("{}:{}", key.raw().trim(), value.compact()));
        }
        parse(&format!("{{{}}}", parts.join(",")))
    }
    /// Serialize the associative maps in insertion order, retaining scalar tokens.
    pub fn compact(&self) -> String {
        let mut out = String::with_capacity(self.raw().len());
        self.write_json(&mut out);
        out
    }
    fn write_json(&self, out: &mut String) {
        match self.kind {
            Kind::Object => {
                out.push('{');
                for (i, (key, value)) in self.members.iter().enumerate() {
                    if i > 0 {
                        out.push(',');
                    }
                    out.push_str(key.raw().trim());
                    out.push(':');
                    value.write_json(out);
                }
                out.push('}');
            }
            Kind::Array => {
                out.push('[');
                for (i, item) in self.items.iter().enumerate() {
                    if i > 0 {
                        out.push(',');
                    }
                    item.write_json(out);
                }
                out.push(']');
            }
            _ => out.push_str(self.raw().trim()),
        }
    }
}
impl fmt::Display for Value {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.compact())
    }
}

pub fn stringify(value: &Value) -> String {
    value.compact()
}
pub fn parse(source: &str) -> Result<Value> {
    parse_with_max_depth(source, MAX_DEPTH)
}
pub fn parse_bytes(source: &[u8]) -> Result<Value> {
    let text = std::str::from_utf8(source).map_err(|e| Error {
        offset: e.valid_up_to(),
        message: "invalid UTF-8",
    })?;
    parse(text)
}
pub fn parse_with_max_depth(source: &str, max_depth: usize) -> Result<Value> {
    if max_depth > MAX_DEPTH {
        return Err(error("max_depth exceeds 256"));
    }
    let mut p = Parser {
        source: Arc::from(source),
        pos: 0,
        max_depth,
    };
    let mut value = p.value(0)?;
    p.ws();
    if p.pos != source.len() {
        return Err(p.error("unexpected trailing input"));
    }
    value.start = 0;
    value.end = source.len();
    Ok(value)
}

struct Parser {
    source: Arc<str>,
    pos: usize,
    max_depth: usize,
}
impl Parser {
    fn peek(&self) -> Option<u8> {
        self.source.as_bytes().get(self.pos).copied()
    }
    fn error(&self, message: &'static str) -> Error {
        Error {
            offset: self.pos,
            message,
        }
    }
    fn ws(&mut self) {
        while matches!(self.peek(), Some(b' ' | b'\n' | b'\r' | b'\t')) {
            self.pos += 1;
        }
    }
    fn expect(&mut self, byte: u8, message: &'static str) -> Result<()> {
        if self.peek() != Some(byte) {
            return Err(self.error(message));
        }
        self.pos += 1;
        Ok(())
    }
    fn string(&mut self) -> Result<Vec<u16>> {
        self.expect(b'"', "expected string")?;
        let mut units = Vec::new();
        while let Some(byte) = self.peek() {
            match byte {
                b'"' => {
                    self.pos += 1;
                    return Ok(units);
                }
                0..=31 => return Err(self.error("unescaped control character")),
                b'\\' => {
                    self.pos += 1;
                    let escape = self.peek().ok_or_else(|| self.error("unfinished escape"))?;
                    self.pos += 1;
                    if escape == b'u' {
                        let mut unit = 0;
                        for _ in 0..4 {
                            let d = self
                                .peek()
                                .and_then(|b| (b as char).to_digit(16))
                                .ok_or_else(|| self.error("invalid Unicode escape"))?;
                            unit = (unit << 4) | d as u16;
                            self.pos += 1;
                        }
                        units.push(unit);
                    } else {
                        units.push(match escape {
                            b'"' => 34,
                            b'\\' => 92,
                            b'/' => 47,
                            b'b' => 8,
                            b'f' => 12,
                            b'n' => 10,
                            b'r' => 13,
                            b't' => 9,
                            _ => return Err(self.error("invalid escape")),
                        });
                    }
                }
                _ => {
                    let ch = self.source[self.pos..].chars().next().unwrap();
                    self.pos += ch.len_utf8();
                    units.extend_from_slice(ch.encode_utf16(&mut [0; 2]));
                }
            }
        }
        Err(self.error("unterminated string"))
    }
    fn digits(&mut self) -> Result<()> {
        if !matches!(self.peek(), Some(b'0'..=b'9')) {
            return Err(self.error("expected digit"));
        }
        while matches!(self.peek(), Some(b'0'..=b'9')) {
            self.pos += 1;
        }
        Ok(())
    }
    fn value(&mut self, depth: usize) -> Result<Value> {
        self.ws();
        let start = self.pos;
        let kind;
        let (mut members, mut items, mut units) = (OrderedMap::new(), Vec::new(), Vec::new());
        match self.peek() {
            Some(open @ (b'{' | b'[')) => {
                if depth >= self.max_depth {
                    return Err(self.error("maximum nesting depth exceeded"));
                }
                kind = if open == b'{' {
                    Kind::Object
                } else {
                    Kind::Array
                };
                let close = if open == b'{' { b'}' } else { b']' };
                self.pos += 1;
                self.ws();
                if self.peek() != Some(close) {
                    loop {
                        if kind == Kind::Object {
                            let key_start = self.pos;
                            let key_units = self.string()?;
                            let key = Value {
                                source: self.source.clone(),
                                start: key_start,
                                end: self.pos,
                                kind: Kind::String,
                                units: key_units,
                                members: OrderedMap::new(),
                                items: Vec::new(),
                            };
                            self.ws();
                            self.expect(b':', "expected colon")?;
                            members.insert(key, self.value(depth + 1)?)?;
                        } else {
                            items.push(self.value(depth + 1)?);
                        }
                        self.ws();
                        if self.peek() == Some(close) {
                            break;
                        }
                        self.expect(b',', "expected comma or closing delimiter")?;
                        self.ws();
                    }
                }
                self.pos += 1;
            }
            Some(b'"') => {
                kind = Kind::String;
                units = self.string()?;
            }
            Some(b'-' | b'0'..=b'9') => {
                kind = Kind::Number;
                if self.peek() == Some(b'-') {
                    self.pos += 1;
                }
                if self.peek() == Some(b'0') {
                    self.pos += 1;
                } else {
                    self.digits()?;
                }
                if self.peek() == Some(b'.') {
                    self.pos += 1;
                    self.digits()?;
                }
                if matches!(self.peek(), Some(b'e' | b'E')) {
                    self.pos += 1;
                    if matches!(self.peek(), Some(b'+' | b'-')) {
                        self.pos += 1;
                    }
                    self.digits()?;
                }
            }
            _ => {
                let tail = &self.source[self.pos..];
                let literal = ["true", "false", "null"]
                    .into_iter()
                    .find(|s| tail.starts_with(s))
                    .ok_or_else(|| self.error("expected JSON value"))?;
                kind = if literal == "null" {
                    Kind::Null
                } else {
                    Kind::Boolean
                };
                self.pos += literal.len();
            }
        }
        Ok(Value {
            source: self.source.clone(),
            start,
            end: self.pos,
            kind,
            members,
            items,
            units,
        })
    }
}
