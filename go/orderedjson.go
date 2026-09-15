// Package orderedjson preserves JSON document order at every object depth.
package orderedjson

import (
	"encoding/json"
	"fmt"
	"strings"
	"unicode/utf16"
	"unicode/utf8"
)

const MaxDepth = 256

type Kind string

const (
	ObjectKind  Kind = "object"
	ArrayKind   Kind = "array"
	StringKind  Kind = "string"
	NumberKind  Kind = "number"
	BooleanKind Kind = "boolean"
	NullKind    Kind = "null"
)

type ParseError struct {
	Offset  int
	Message string
}

func (e *ParseError) Error() string { return fmt.Sprintf("%s at byte %d", e.Message, e.Offset) }

// OrderedMap associates each key with one value and retains its insertion position.
// Its zero value is an empty map. Keys returns JSON string values in that order.
type OrderedMap struct {
	state *orderedMapState
}

type orderedMapState struct {
	keys   []*Value
	values map[string]*Value
}

// unitsKey is a lossless identity for decoded JSON keys, including lone surrogates.
func unitsKey(units []uint16) string {
	key := make([]byte, len(units)*2)
	for i, unit := range units {
		key[2*i], key[2*i+1] = byte(unit>>8), byte(unit)
	}
	return string(key)
}
func (m *OrderedMap) Set(key, value *Value) error {
	if key.Kind() != StringKind {
		return fmt.Errorf("object key must be string")
	}
	if !value.valid() {
		return fmt.Errorf("expected orderedjson Value")
	}
	if m.state == nil {
		m.state = &orderedMapState{values: make(map[string]*Value)}
	}
	name := unitsKey(key.units)
	if _, exists := m.state.values[name]; !exists {
		m.state.keys = append(m.state.keys, key)
	}
	m.state.values[name] = value
	return nil
}
func (m *OrderedMap) GetUnits(key []uint16) *Value {
	if m.state == nil {
		return nil
	}
	return m.state.values[unitsKey(key)]
}
func (m *OrderedMap) Get(key string) *Value {
	if !utf8.ValidString(key) {
		return nil
	}
	return m.GetUnits(utf16.Encode([]rune(key)))
}
func (m *OrderedMap) orderedKeys() []*Value {
	if m.state == nil {
		return nil
	}
	return m.state.keys
}
func (m *OrderedMap) Keys() []*Value { return append([]*Value{}, m.orderedKeys()...) }
func (m *OrderedMap) Len() int       { return len(m.orderedKeys()) }
func (m *OrderedMap) clone() *OrderedMap {
	out := &OrderedMap{}
	if m.state == nil {
		return out
	}
	out.state = &orderedMapState{keys: m.Keys(), values: make(map[string]*Value, m.Len())}
	for key, value := range m.state.values {
		out.state.values[key] = value
	}
	return out
}

// Value is immutable. Construct values with Parse or the factory functions.
// The zero value is invalid. Members and Items return independent map/slice copies.
type Value struct {
	source     string
	start, end int
	kind       Kind
	members    OrderedMap
	items      []*Value
	units      []uint16
}

func (v *Value) valid() bool { return v != nil && v.kind != "" }
func (v *Value) Kind() Kind {
	if !v.valid() {
		return ""
	}
	return v.kind
}
func (v *Value) Raw() string {
	if !v.valid() {
		return ""
	}
	return v.source[v.start:v.end]
}
func (v *Value) String() string { out, _ := v.Compact(); return out }
func (v *Value) Members() (*OrderedMap, error) {
	if v.Kind() != ObjectKind {
		return nil, fmt.Errorf("expected object")
	}
	return v.members.clone(), nil
}
func (v *Value) Items() ([]*Value, error) {
	if v.Kind() != ArrayKind {
		return nil, fmt.Errorf("expected array")
	}
	return append([]*Value{}, v.items...), nil
}
func (v *Value) StringUnits() ([]uint16, error) {
	if v.Kind() != StringKind {
		return nil, fmt.Errorf("expected string")
	}
	return append([]uint16{}, v.units...), nil
}
func (v *Value) StringValue() (string, error) {
	if v.Kind() != StringKind {
		return "", fmt.Errorf("expected string")
	}
	for i := 0; i < len(v.units); i++ {
		u := v.units[i]
		if u >= 0xd800 && u <= 0xdbff {
			if i+1 >= len(v.units) || v.units[i+1] < 0xdc00 || v.units[i+1] > 0xdfff {
				return "", fmt.Errorf("unpaired surrogate; use StringUnits")
			}
			i++
		} else if u >= 0xdc00 && u <= 0xdfff {
			return "", fmt.Errorf("unpaired surrogate; use StringUnits")
		}
	}
	return string(utf16.Decode(v.units)), nil
}
func (v *Value) NumberLiteral() (string, error) {
	if v.Kind() != NumberKind {
		return "", fmt.Errorf("expected number")
	}
	return strings.TrimSpace(v.Raw()), nil
}
func (v *Value) BooleanValue() (bool, error) {
	if v.Kind() != BooleanKind {
		return false, fmt.Errorf("expected boolean")
	}
	return strings.TrimSpace(v.Raw()) == "true", nil
}
func (v *Value) GetUnits(key []uint16) *Value {
	if v.Kind() != ObjectKind {
		return nil
	}
	return v.members.GetUnits(key)
}
func (v *Value) Get(key string) *Value {
	if !utf8.ValidString(key) {
		return nil
	}
	return v.GetUnits(utf16.Encode([]rune(key)))
}
func String(text string) (*Value, error) {
	if !utf8.ValidString(text) {
		return nil, fmt.Errorf("invalid UTF-8")
	}
	raw, err := json.Marshal(text)
	if err != nil {
		return nil, err
	}
	return Parse(string(raw))
}
func StringFromUnits(units []uint16) *Value {
	var out strings.Builder
	out.WriteByte('"')
	for _, u := range units {
		fmt.Fprintf(&out, "\\u%04x", u)
	}
	out.WriteByte('"')
	v, _ := Parse(out.String())
	return v
}
func Number(literal string) (*Value, error) {
	v, err := Parse(literal)
	if err != nil {
		return nil, err
	}
	if v.kind != NumberKind || strings.TrimSpace(literal) != literal {
		return nil, fmt.Errorf("expected number literal without whitespace")
	}
	return v, nil
}
func Boolean(value bool) *Value {
	if value {
		v, _ := Parse("true")
		return v
	}
	v, _ := Parse("false")
	return v
}
func Null() *Value { v, _ := Parse("null"); return v }
func Array(items []*Value) (*Value, error) {
	parts := make([]string, len(items))
	for i, v := range items {
		if !v.valid() {
			return nil, fmt.Errorf("expected orderedjson Value")
		}
		parts[i], _ = v.Compact()
	}
	return Parse("[" + strings.Join(parts, ",") + "]")
}
func Object(members *OrderedMap) (*Value, error) {
	if members == nil {
		return nil, fmt.Errorf("expected ordered map")
	}
	parts := make([]string, members.Len())
	for i, key := range members.orderedKeys() {
		child, _ := members.GetUnits(key.units).Compact()
		parts[i] = strings.TrimSpace(key.Raw()) + ":" + child
	}
	return Parse("{" + strings.Join(parts, ",") + "}")
}
func Stringify(value *Value) (string, error) {
	if !value.valid() {
		return "", fmt.Errorf("expected orderedjson Value")
	}
	return value.Compact()
}

// MarshalJSON preserves members and literals; encoding/json may compact/escape the result.
func (v *Value) MarshalJSON() ([]byte, error) {
	raw, err := Stringify(v)
	return []byte(raw), err
}
func (v *Value) Compact() (string, error) {
	if !v.valid() {
		return "", fmt.Errorf("expected orderedjson Value")
	}
	var out strings.Builder
	v.writeJSON(&out)
	return out.String(), nil
}
func (v *Value) writeJSON(out *strings.Builder) {
	switch v.kind {
	case ObjectKind:
		out.WriteByte('{')
		for i, key := range v.members.orderedKeys() {
			if i > 0 {
				out.WriteByte(',')
			}
			out.WriteString(strings.TrimSpace(key.Raw()))
			out.WriteByte(':')
			v.members.GetUnits(key.units).writeJSON(out)
		}
		out.WriteByte('}')
	case ArrayKind:
		out.WriteByte('[')
		for i, item := range v.items {
			if i > 0 {
				out.WriteByte(',')
			}
			item.writeJSON(out)
		}
		out.WriteByte(']')
	default:
		out.WriteString(strings.TrimSpace(v.Raw()))
	}
}

func Parse(source string) (*Value, error)      { return ParseWithMaxDepth(source, MaxDepth) }
func ParseBytes(source []byte) (*Value, error) { return Parse(string(source)) }
func ParseWithMaxDepth(source string, maxDepth int) (*Value, error) {
	if maxDepth < 0 || maxDepth > MaxDepth {
		return nil, fmt.Errorf("maxDepth must be between 0 and 256")
	}
	if !utf8.ValidString(source) {
		return nil, &ParseError{0, "invalid UTF-8"}
	}
	p := parser{source: source, maxDepth: maxDepth}
	v, err := p.value(0)
	if err != nil {
		return nil, err
	}
	p.ws()
	if p.pos != len(source) {
		return nil, p.fail("unexpected trailing input")
	}
	v.start = 0
	v.end = len(source)
	return v, nil
}

type parser struct {
	source        string
	pos, maxDepth int
}

func (p *parser) peek() byte {
	if p.pos >= len(p.source) {
		return 0
	}
	return p.source[p.pos]
}
func (p *parser) fail(message string) error { return &ParseError{p.pos, message} }
func (p *parser) ws() {
	for p.peek() == ' ' || p.peek() == '\t' || p.peek() == '\n' || p.peek() == '\r' {
		p.pos++
	}
}
func (p *parser) expect(ch byte, message string) error {
	if p.peek() != ch {
		return p.fail(message)
	}
	p.pos++
	return nil
}
func hex(ch byte) (uint16, bool) {
	switch {
	case ch >= '0' && ch <= '9':
		return uint16(ch - '0'), true
	case ch >= 'a' && ch <= 'f':
		return uint16(ch - 'a' + 10), true
	case ch >= 'A' && ch <= 'F':
		return uint16(ch - 'A' + 10), true
	}
	return 0, false
}
func (p *parser) stringUnits() ([]uint16, error) {
	if err := p.expect('"', "expected string"); err != nil {
		return nil, err
	}
	units := []uint16{}
	for p.pos < len(p.source) {
		ch := p.peek()
		p.pos++
		switch {
		case ch == '"':
			return units, nil
		case ch < 32:
			return nil, p.fail("unescaped control character")
		case ch == '\\':
			escape := p.peek()
			if p.pos >= len(p.source) {
				return nil, p.fail("unfinished escape")
			}
			p.pos++
			if escape == 'u' {
				var u uint16
				for i := 0; i < 4; i++ {
					d, ok := hex(p.peek())
					if !ok {
						return nil, p.fail("invalid Unicode escape")
					}
					u = u<<4 | d
					p.pos++
				}
				units = append(units, u)
			} else {
				var u uint16
				switch escape {
				case '"', '\\', '/':
					u = uint16(escape)
				case 'b':
					u = 8
				case 'f':
					u = 12
				case 'n':
					u = 10
				case 'r':
					u = 13
				case 't':
					u = 9
				default:
					return nil, p.fail("invalid escape")
				}
				units = append(units, u)
			}
		case ch < 128:
			units = append(units, uint16(ch))
		default:
			p.pos--
			r, width := utf8.DecodeRuneInString(p.source[p.pos:])
			p.pos += width
			units = append(units, utf16.Encode([]rune{r})...)
		}
	}
	return nil, p.fail("unterminated string")
}
func isDigit(ch byte) bool { return ch >= '0' && ch <= '9' }
func (p *parser) digits() error {
	if !isDigit(p.peek()) {
		return p.fail("expected digit")
	}
	for isDigit(p.peek()) {
		p.pos++
	}
	return nil
}
func (p *parser) value(depth int) (*Value, error) {
	p.ws()
	v := &Value{source: p.source, start: p.pos}
	switch ch := p.peek(); {
	case ch == '{' || ch == '[':
		if depth >= p.maxDepth {
			return nil, p.fail("maximum nesting depth exceeded")
		}
		close := byte(']')
		v.kind = ArrayKind
		if ch == '{' {
			close = '}'
			v.kind = ObjectKind
		}
		p.pos++
		p.ws()
		if p.peek() != close {
			for {
				if v.kind == ObjectKind {
					start := p.pos
					units, err := p.stringUnits()
					if err != nil {
						return nil, err
					}
					key := &Value{source: p.source, start: start, end: p.pos, kind: StringKind, units: units}
					p.ws()
					if err := p.expect(':', "expected colon"); err != nil {
						return nil, err
					}
					child, err := p.value(depth + 1)
					if err != nil {
						return nil, err
					}
					if err := v.members.Set(key, child); err != nil {
						return nil, err
					}
				} else {
					child, err := p.value(depth + 1)
					if err != nil {
						return nil, err
					}
					v.items = append(v.items, child)
				}
				p.ws()
				if p.peek() == close {
					break
				}
				if err := p.expect(',', "expected comma or closing delimiter"); err != nil {
					return nil, err
				}
				p.ws()
			}
		}
		p.pos++
	case ch == '"':
		v.kind = StringKind
		units, err := p.stringUnits()
		if err != nil {
			return nil, err
		}
		v.units = units
	case ch == '-' || isDigit(ch):
		v.kind = NumberKind
		if p.peek() == '-' {
			p.pos++
		}
		if p.peek() == '0' {
			p.pos++
		} else if err := p.digits(); err != nil {
			return nil, err
		}
		if p.peek() == '.' {
			p.pos++
			if err := p.digits(); err != nil {
				return nil, err
			}
		}
		if p.peek() == 'e' || p.peek() == 'E' {
			p.pos++
			if p.peek() == '+' || p.peek() == '-' {
				p.pos++
			}
			if err := p.digits(); err != nil {
				return nil, err
			}
		}
	default:
		found := false
		for _, literal := range []string{"true", "false", "null"} {
			if strings.HasPrefix(p.source[p.pos:], literal) {
				p.pos += len(literal)
				v.kind = BooleanKind
				if literal == "null" {
					v.kind = NullKind
				}
				found = true
				break
			}
		}
		if !found {
			return nil, p.fail("expected JSON value")
		}
	}
	v.end = p.pos
	return v, nil
}
