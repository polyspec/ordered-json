//! Serde binding for typed JSON values.
use ::serde::{
    de::{self, DeserializeOwned},
    ser::{
        self, Serialize, SerializeMap, SerializeSeq, SerializeStruct, SerializeStructVariant,
        SerializeTuple, SerializeTupleStruct, SerializeTupleVariant,
    },
    Deserialize,
};
use serde_json::value::RawValue;
const RAW_TOKEN: &str = "$serde_json::private::RawValue";
use std::{collections::HashSet, fmt};

#[derive(Debug)]
pub enum Error {
    Json(super::Error),
    Typed(serde_json::Error),
    Encode(String),
}
impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Json(e) => e.fmt(f),
            Self::Typed(e) => e.fmt(f),
            Self::Encode(e) => f.write_str(e),
        }
    }
}
impl std::error::Error for Error {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Json(e) => Some(e),
            Self::Typed(e) => Some(e),
            Self::Encode(_) => None,
        }
    }
}
impl ser::Error for Error {
    fn custom<T: fmt::Display>(v: T) -> Self {
        Self::Encode(v.to_string())
    }
}

pub fn to_string<T: Serialize + ?Sized>(value: &T) -> Result<String, Error> {
    let mut w = Writer {
        text: String::new(),
        depth: 0,
    };
    value.serialize(&mut w)?;
    Ok(super::parse(&w.text).map_err(Error::Json)?.compact())
}
pub fn from_slice<T: DeserializeOwned>(bytes: &[u8]) -> Result<T, Error> {
    let value = super::parse_bytes_reject_duplicates(bytes).map_err(Error::Json)?;
    let text = value.compact();
    let mut decoder = serde_json::Deserializer::from_str(&text);
    decoder.disable_recursion_limit();
    let mut ignored = None;
    let result = serde_ignored::deserialize(&mut decoder, |path| {
        if ignored.is_none() {
            ignored = Some(path.to_string());
        }
    })
    .map_err(Error::Typed)?;
    decoder.end().map_err(Error::Typed)?;
    if let Some(path) = ignored {
        return Err(Error::Encode(format!("unknown field: {path}")));
    }
    Ok(result)
}
pub fn from_str<T: DeserializeOwned>(text: &str) -> Result<T, Error> {
    from_slice(text.as_bytes())
}

impl Serialize for super::Value {
    fn serialize<S: ser::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        let text = self.compact();
        let mut decoder = serde_json::Deserializer::from_str(&text);
        decoder.disable_recursion_limit();
        let raw = Box::<RawValue>::deserialize(&mut decoder).map_err(ser::Error::custom)?;
        decoder.end().map_err(ser::Error::custom)?;
        raw.serialize(serializer)
    }
}

impl<'de> Deserialize<'de> for super::Value {
    fn deserialize<D: de::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        let raw = Box::<RawValue>::deserialize(deserializer)?;
        super::parse_bytes_reject_duplicates(raw.get().as_bytes()).map_err(de::Error::custom)
    }
}

struct Writer {
    text: String,
    depth: usize,
}
impl Writer {
    fn quoted(&mut self, v: &str) -> Result<(), Error> {
        self.text
            .push_str(&serde_json::to_string(v).map_err(Error::Typed)?);
        Ok(())
    }
    fn begin(&mut self, c: char) -> Result<(), Error> {
        if self.depth >= super::MAX_DEPTH {
            return Err(Error::Encode("maximum nesting depth exceeded".into()));
        }
        self.depth += 1;
        self.text.push(c);
        Ok(())
    }
    fn end(&mut self, c: char) {
        self.depth -= 1;
        self.text.push(c)
    }
}
struct Compound<'a> {
    w: &'a mut Writer,
    first: bool,
    close: char,
    keys: Option<HashSet<String>>,
    pending: bool,
    variant: bool,
    raw: bool,
}
impl Compound<'_> {
    fn comma(&mut self) {
        if !self.first {
            self.w.text.push(',')
        }
        self.first = false
    }
    fn key(&mut self, k: &str) -> Result<(), Error> {
        if self.pending {
            return Err(Error::Encode("map value is missing".into()));
        }
        if !self
            .keys
            .as_mut()
            .ok_or_else(|| Error::Encode("object key is invalid".into()))?
            .insert(k.into())
        {
            return Err(Error::Encode(format!("duplicate object key: {k}")));
        }
        self.comma();
        self.w.quoted(k)?;
        self.w.text.push(':');
        self.pending = true;
        Ok(())
    }
    fn value<T: Serialize + ?Sized>(&mut self, v: &T) -> Result<(), Error> {
        if !self.pending {
            self.comma()
        }
        v.serialize(&mut *self.w)?;
        self.pending = false;
        Ok(())
    }
    fn finish(self) -> Result<(), Error> {
        if self.raw {
            return if self.first {
                Err(Error::Encode("raw JSON value is missing".into()))
            } else {
                Ok(())
            };
        }
        if self.pending {
            return Err(Error::Encode("map value is missing".into()));
        }
        self.w.end(self.close);
        if self.variant {
            self.w.end('}')
        }
        Ok(())
    }
}
impl<'a> ser::Serializer for &'a mut Writer {
    type Ok = ();
    type Error = Error;
    type SerializeSeq = Compound<'a>;
    type SerializeTuple = Compound<'a>;
    type SerializeTupleStruct = Compound<'a>;
    type SerializeTupleVariant = Compound<'a>;
    type SerializeMap = Compound<'a>;
    type SerializeStruct = Compound<'a>;
    type SerializeStructVariant = Compound<'a>;
    fn serialize_bool(self, v: bool) -> Result<(), Error> {
        self.text.push_str(if v { "true" } else { "false" });
        Ok(())
    }
    fn serialize_i8(self, v: i8) -> Result<(), Error> {
        self.serialize_i64(v.into())
    }
    fn serialize_i16(self, v: i16) -> Result<(), Error> {
        self.serialize_i64(v.into())
    }
    fn serialize_i32(self, v: i32) -> Result<(), Error> {
        self.serialize_i64(v.into())
    }
    fn serialize_i64(self, v: i64) -> Result<(), Error> {
        self.text.push_str(&v.to_string());
        Ok(())
    }
    fn serialize_i128(self, v: i128) -> Result<(), Error> {
        self.text.push_str(&v.to_string());
        Ok(())
    }
    fn serialize_u8(self, v: u8) -> Result<(), Error> {
        self.serialize_u64(v.into())
    }
    fn serialize_u16(self, v: u16) -> Result<(), Error> {
        self.serialize_u64(v.into())
    }
    fn serialize_u32(self, v: u32) -> Result<(), Error> {
        self.serialize_u64(v.into())
    }
    fn serialize_u64(self, v: u64) -> Result<(), Error> {
        self.text.push_str(&v.to_string());
        Ok(())
    }
    fn serialize_u128(self, v: u128) -> Result<(), Error> {
        self.text.push_str(&v.to_string());
        Ok(())
    }
    fn serialize_f32(self, v: f32) -> Result<(), Error> {
        if !v.is_finite() {
            return Err(Error::Encode("non-finite number".into()));
        }
        self.text
            .push_str(&serde_json::to_string(&v).map_err(Error::Typed)?);
        Ok(())
    }
    fn serialize_f64(self, v: f64) -> Result<(), Error> {
        if !v.is_finite() {
            return Err(Error::Encode("non-finite number".into()));
        }
        self.text
            .push_str(&serde_json::to_string(&v).map_err(Error::Typed)?);
        Ok(())
    }
    fn serialize_char(self, v: char) -> Result<(), Error> {
        self.quoted(&v.to_string())
    }
    fn serialize_str(self, v: &str) -> Result<(), Error> {
        self.quoted(v)
    }
    fn serialize_bytes(self, v: &[u8]) -> Result<(), Error> {
        let mut s = self.serialize_seq(Some(v.len()))?;
        for b in v {
            SerializeSeq::serialize_element(&mut s, b)?
        }
        SerializeSeq::end(s)
    }
    fn serialize_none(self) -> Result<(), Error> {
        self.serialize_unit()
    }
    fn serialize_some<T: Serialize + ?Sized>(self, v: &T) -> Result<(), Error> {
        v.serialize(self)
    }
    fn serialize_unit(self) -> Result<(), Error> {
        self.text.push_str("null");
        Ok(())
    }
    fn serialize_unit_struct(self, _: &'static str) -> Result<(), Error> {
        self.serialize_unit()
    }
    fn serialize_unit_variant(self, _: &'static str, _: u32, n: &'static str) -> Result<(), Error> {
        self.quoted(n)
    }
    fn serialize_newtype_struct<T: Serialize + ?Sized>(
        self,
        _: &'static str,
        v: &T,
    ) -> Result<(), Error> {
        v.serialize(self)
    }
    fn serialize_newtype_variant<T: Serialize + ?Sized>(
        self,
        _: &'static str,
        _: u32,
        n: &'static str,
        v: &T,
    ) -> Result<(), Error> {
        self.begin('{')?;
        self.quoted(n)?;
        self.text.push(':');
        v.serialize(&mut *self)?;
        self.end('}');
        Ok(())
    }
    fn serialize_seq(self, _: Option<usize>) -> Result<Compound<'a>, Error> {
        self.begin('[')?;
        Ok(Compound {
            w: self,
            first: true,
            close: ']',
            keys: None,
            pending: false,
            variant: false,
            raw: false,
        })
    }
    fn serialize_tuple(self, n: usize) -> Result<Compound<'a>, Error> {
        self.serialize_seq(Some(n))
    }
    fn serialize_tuple_struct(self, _: &'static str, n: usize) -> Result<Compound<'a>, Error> {
        self.serialize_seq(Some(n))
    }
    fn serialize_tuple_variant(
        self,
        _: &'static str,
        _: u32,
        n: &'static str,
        _: usize,
    ) -> Result<Compound<'a>, Error> {
        self.begin('{')?;
        self.quoted(n)?;
        self.text.push(':');
        self.begin('[')?;
        Ok(Compound {
            w: self,
            first: true,
            close: ']',
            keys: None,
            pending: false,
            variant: true,
            raw: false,
        })
    }
    fn serialize_map(self, _: Option<usize>) -> Result<Compound<'a>, Error> {
        self.begin('{')?;
        Ok(Compound {
            w: self,
            first: true,
            close: '}',
            keys: Some(HashSet::new()),
            pending: false,
            variant: false,
            raw: false,
        })
    }
    fn serialize_struct(self, name: &'static str, n: usize) -> Result<Compound<'a>, Error> {
        if name == RAW_TOKEN {
            return Ok(Compound {
                w: self,
                first: true,
                close: '\0',
                keys: None,
                pending: false,
                variant: false,
                raw: true,
            });
        }
        self.serialize_map(Some(n))
    }
    fn serialize_struct_variant(
        self,
        _: &'static str,
        _: u32,
        n: &'static str,
        _: usize,
    ) -> Result<Compound<'a>, Error> {
        self.begin('{')?;
        self.quoted(n)?;
        self.text.push(':');
        self.begin('{')?;
        Ok(Compound {
            w: self,
            first: true,
            close: '}',
            keys: Some(HashSet::new()),
            pending: false,
            variant: true,
            raw: false,
        })
    }
    fn collect_str<T: fmt::Display + ?Sized>(self, v: &T) -> Result<(), Error> {
        self.quoted(&v.to_string())
    }
}
impl SerializeSeq for Compound<'_> {
    type Ok = ();
    type Error = Error;
    fn serialize_element<T: Serialize + ?Sized>(&mut self, v: &T) -> Result<(), Error> {
        self.value(v)
    }
    fn end(self) -> Result<(), Error> {
        self.finish()
    }
}
impl SerializeTuple for Compound<'_> {
    type Ok = ();
    type Error = Error;
    fn serialize_element<T: Serialize + ?Sized>(&mut self, v: &T) -> Result<(), Error> {
        self.value(v)
    }
    fn end(self) -> Result<(), Error> {
        self.finish()
    }
}
impl SerializeTupleStruct for Compound<'_> {
    type Ok = ();
    type Error = Error;
    fn serialize_field<T: Serialize + ?Sized>(&mut self, v: &T) -> Result<(), Error> {
        self.value(v)
    }
    fn end(self) -> Result<(), Error> {
        self.finish()
    }
}
impl SerializeTupleVariant for Compound<'_> {
    type Ok = ();
    type Error = Error;
    fn serialize_field<T: Serialize + ?Sized>(&mut self, v: &T) -> Result<(), Error> {
        self.value(v)
    }
    fn end(self) -> Result<(), Error> {
        self.finish()
    }
}
impl SerializeMap for Compound<'_> {
    type Ok = ();
    type Error = Error;
    fn serialize_key<T: Serialize + ?Sized>(&mut self, k: &T) -> Result<(), Error> {
        let v = serde_json::to_value(k).map_err(Error::Typed)?;
        self.key(
            v.as_str()
                .ok_or_else(|| Error::Encode("object key must be a string".into()))?,
        )
    }
    fn serialize_value<T: Serialize + ?Sized>(&mut self, v: &T) -> Result<(), Error> {
        if !self.pending {
            return Err(Error::Encode("map key is missing".into()));
        }
        self.value(v)
    }
    fn end(self) -> Result<(), Error> {
        self.finish()
    }
}
impl SerializeStruct for Compound<'_> {
    type Ok = ();
    type Error = Error;
    fn serialize_field<T: Serialize + ?Sized>(
        &mut self,
        k: &'static str,
        v: &T,
    ) -> Result<(), Error> {
        if self.raw {
            if k != RAW_TOKEN || !self.first {
                return Err(Error::Encode("invalid raw JSON field".into()));
            }
            let value = serde_json::to_value(v).map_err(Error::Typed)?;
            let text = value
                .as_str()
                .ok_or_else(|| Error::Encode("raw JSON must be text".into()))?;
            self.w
                .text
                .push_str(&super::parse(text).map_err(Error::Json)?.compact());
            self.first = false;
            return Ok(());
        }
        self.key(k)?;
        self.value(v)
    }
    fn end(self) -> Result<(), Error> {
        self.finish()
    }
}
impl SerializeStructVariant for Compound<'_> {
    type Ok = ();
    type Error = Error;
    fn serialize_field<T: Serialize + ?Sized>(
        &mut self,
        k: &'static str,
        v: &T,
    ) -> Result<(), Error> {
        self.key(k)?;
        self.value(v)
    }
    fn end(self) -> Result<(), Error> {
        self.finish()
    }
}
